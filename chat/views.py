import json
import PyPDF2
import traceback
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import login, logout, authenticate
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.http import StreamingHttpResponse, JsonResponse
from django.views.decorators.http import require_POST
from django.contrib import messages
from django.conf import settings
from django.utils import timezone
from groq import Groq

from .models import Conversation, Message, UploadedDocument

from django.http import HttpResponse

def diagnostico(request):
    groq_key = settings.GROQ_API_KEY
    return HttpResponse(f"GROQ_API_KEY configurada: {'SIM - ' + groq_key[:8] + '...' if groq_key else 'NÃO - VAZIA'}")

SYSTEM_PROMPT = """Você é um assistente especializado em IRPF (Imposto de Renda de Pessoa Física) do Brasil, integrado ao sistema de um escritório de contabilidade. Seu papel é ajudar contadores e funcionários a esclarecer dúvidas técnicas sobre:

- Declaração do IRPF: modelo completo vs simplificado, prazo, multas por atraso
- Rendimentos tributáveis (salário, aluguel, autônomo, pró-labore) e isentos (FGTS, indenizações, aposentadoria até limite)
- Deduções legais: saúde (sem limite), educação (limite anual), dependentes, previdência oficial e privada (PGBL até 12% da renda), pensão alimentícia judicial
- Bens e direitos: imóveis, veículos, ações, contas bancárias — custo de aquisição vs valor de mercado
- Ganho de capital: cálculo, isenções (imóvel único até R$440k, venda abaixo R$35k/mês), alíquotas progressivas
- Renda variável: Day trade (20%), swing trade (15%), isenção até R$20k/mês em ações
- Carnê-leão: obrigatoriedade, cálculo mensal, importação na declaração
- Malha fina: causas comuns (despesas médicas sem comprovante, divergência de informe, omissão de rendimentos)
- Retificação: prazo, como proceder, impacto em restituição ou imposto a pagar
- MEI e autônomos: DASN, DIRF, retenções na fonte

Responda sempre em português brasileiro, de forma clara e profissional. Use exemplos com valores reais quando ajudar. Cite a legislação relevante (Lei 9.250/95, IN RFB, etc.) quando pertinente. Se o contexto incluir documentos do cliente, baseie sua análise neles. Nunca invente valores ou regras — se não tiver certeza, oriente a consultar o site da Receita Federal (receita.fazenda.gov.br)."""


# ─── Auth ────────────────────────────────────────────────────────────────────

def login_view(request):
    if request.user.is_authenticated:
        return redirect('chat:index')
    if request.method == 'POST':
        username = request.POST.get('username', '').strip()
        password = request.POST.get('password', '')
        user = authenticate(request, username=username, password=password)
        if user:
            login(request, user)
            return redirect(request.GET.get('next', 'chat:index'))
        messages.error(request, 'Usuário ou senha incorretos.')
    return render(request, 'chat/login.html')


def logout_view(request):
    logout(request)
    return redirect('chat:login')


# ─── Main chat ───────────────────────────────────────────────────────────────

@login_required
def index(request):
    conversations = request.user.conversations.all()
    return render(request, 'chat/index.html', {'conversations': conversations})


@login_required
def conversation_detail(request, pk):
    conversation = get_object_or_404(Conversation, pk=pk, user=request.user)
    conversations = request.user.conversations.all()
    chat_messages = conversation.messages.all()
    documents = conversation.documents.all()
    return render(request, 'chat/index.html', {
        'conversations': conversations,
        'active_conversation': conversation,
        'chat_messages': chat_messages,
        'documents': documents,
    })


@login_required
@require_POST
def new_conversation(request):
    conv = Conversation.objects.create(user=request.user)
    return redirect('chat:conversation', pk=conv.pk)


@login_required
@require_POST
def delete_conversation(request, pk):
    conv = get_object_or_404(Conversation, pk=pk, user=request.user)
    conv.delete()
    return redirect('chat:index')


# ─── Chat ────────────────────────────────────────────────────────────────────

@login_required
@require_POST
def send_message(request, pk):
    conversation = get_object_or_404(Conversation, pk=pk, user=request.user)
    data = json.loads(request.body)
    user_input = data.get('message', '').strip()
    if not user_input:
        return JsonResponse({'error': 'Mensagem vazia'}, status=400)

    # Limite de 100 mensagens por dia por usuário
    hoje = timezone.now().date()
    mensagens_hoje = Message.objects.filter(
        conversation__user=request.user,
        role='user',
        created_at__date=hoje
    ).count()
    if mensagens_hoje >= 100:
        return JsonResponse({
            'error': 'Você atingiu o limite de 100 mensagens por dia. Tente novamente amanhã.'
        }, status=429)

    # Salva mensagem do usuário
    Message.objects.create(conversation=conversation, role='user', content=user_input)

    # Contexto de documentos
    doc_context = ''
    for doc in conversation.documents.all():
        if doc.extracted_text:
            doc_context += f"\n\n[Documento: {doc.original_name}]\n{doc.extracted_text[:3000]}"

    system = SYSTEM_PROMPT + (f"\n\nDocumentos do cliente disponíveis:{doc_context}" if doc_context else '')

    # Histórico
    all_messages = list(conversation.messages.all().order_by('created_at'))
    history = [
        {'role': m.role, 'content': m.content}
        for m in all_messages[:-1][-19:]
    ]
    history.append({'role': 'user', 'content': user_input})

    def stream_response():
        client = Groq(api_key=settings.GROQ_API_KEY)
        full_response = ''
        try:
            response = client.chat.completions.create(
                model='llama-3.3-70b-versatile',
                messages=[{'role': 'system', 'content': system}] + history,
                stream=False,
                max_tokens=1500,
            )
            full_response = response.choices[0].message.content or ''
            yield f"data: {json.dumps({'text': full_response})}\n\n"
        except Exception as e:
            print(f"ERRO GROQ: {str(e)}")
            print(traceback.format_exc())
            yield f"data: {json.dumps({'error': str(e)})}\n\n"
            return

        Message.objects.create(conversation=conversation, role='assistant', content=full_response)
        if conversation.title == 'Nova conversa' and len(user_input) > 5:
            conversation.title = user_input[:60] + ('…' if len(user_input) > 60 else '')
            conversation.save()

        yield f"data: {json.dumps({'done': True, 'title': conversation.title, 'conv_id': conversation.pk})}\n\n"

    return StreamingHttpResponse(stream_response(), content_type='text/event-stream')


# ─── Document upload ─────────────────────────────────────────────────────────

@login_required
@require_POST
def upload_document(request, pk):
    conversation = get_object_or_404(Conversation, pk=pk, user=request.user)
    uploaded_file = request.FILES.get('document')
    if not uploaded_file:
        return JsonResponse({'error': 'Nenhum arquivo enviado'}, status=400)
    if uploaded_file.size > settings.MAX_UPLOAD_SIZE:
        return JsonResponse({'error': 'Arquivo muito grande (máx 10MB)'}, status=400)
    if not uploaded_file.name.lower().endswith('.pdf'):
        return JsonResponse({'error': 'Apenas arquivos PDF são aceitos'}, status=400)

    extracted = ''
    try:
        reader = PyPDF2.PdfReader(uploaded_file)
        for page in reader.pages:
            extracted += page.extract_text() or ''
        uploaded_file.seek(0)
    except Exception:
        extracted = ''

    doc = UploadedDocument.objects.create(
        user=request.user,
        conversation=conversation,
        file=uploaded_file,
        original_name=uploaded_file.name,
        extracted_text=extracted,
    )
    return JsonResponse({
        'id': doc.pk,
        'name': doc.original_name,
        'has_text': bool(extracted),
    })


@login_required
@require_POST
def delete_document(request, doc_pk):
    doc = get_object_or_404(UploadedDocument, pk=doc_pk, user=request.user)
    doc.file.delete(save=False)
    doc.delete()
    return JsonResponse({'ok': True})