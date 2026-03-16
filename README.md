# IRPF Chat — Escritório Contábil

Chat especializado em IRPF com Django + API Claude (Anthropic).

## Funcionalidades
- Login restrito (admin cria usuários)
- Histórico de conversas por usuário
- Upload de PDF para contexto
- Streaming de respostas
- Painel admin Django

---

## Instalação local

```bash
# 1. Clonar e entrar na pasta
cd irpf_chat

# 2. Criar ambiente virtual
python -m venv venv
source venv/bin/activate        # Linux/Mac
venv\Scripts\activate           # Windows

# 3. Instalar dependências
pip install -r requirements.txt

# 4. Configurar variáveis de ambiente
cp .env.example .env
# Edite o .env com sua ANTHROPIC_API_KEY e SECRET_KEY

# 5. Migrar banco
python manage.py migrate

# 6. Criar superusuário (admin)
python manage.py createsuperuser

# 7. Rodar servidor
python manage.py runserver
```

Acesse: http://localhost:8000

---

## Criar usuários para funcionários

1. Acesse http://localhost:8000/admin
2. Faça login com o superusuário criado acima
3. Clique em **Usuários > Adicionar usuário**
4. Preencha nome de usuário e senha
5. Clique em salvar e adicione nome, e-mail se quiser

---

## Deploy no Railway

### Pré-requisitos
- Conta no [Railway](https://railway.app) (free tier disponível)
- Conta na [Anthropic](https://console.anthropic.com) para a API key

### Passo a passo

**1. Criar projeto no Railway**
- Acesse railway.app → New Project → Deploy from GitHub
- Conecte seu repositório GitHub com este projeto

**2. Adicionar banco PostgreSQL**
- No painel Railway: New → Database → PostgreSQL
- O Railway adiciona `DATABASE_URL` automaticamente

**3. Configurar variáveis de ambiente**
No Railway → seu serviço → Variables, adicione:

```
SECRET_KEY=<gere uma chave em: https://djecrety.ir>
DEBUG=False
ALLOWED_HOSTS=seuapp.railway.app
ANTHROPIC_API_KEY=sk-ant-...
```

**4. Deploy automático**
O Railway detecta o `railway.toml` e faz tudo automaticamente:
- Instala dependências
- Roda `migrate`
- Coleta arquivos estáticos
- Inicia o Gunicorn

**5. Criar superusuário no Railway**
No Railway → seu serviço → Shell:
```bash
python manage.py createsuperuser
```

**6. Pronto!**
Acesse a URL gerada pelo Railway e crie os usuários para sua equipe via /admin.

---

## Estrutura do projeto

```
irpf_chat/
├── irpf_chat/          # Configurações Django
│   ├── settings.py
│   ├── urls.py
│   └── wsgi.py
├── chat/               # App principal
│   ├── models.py       # Conversation, Message, UploadedDocument
│   ├── views.py        # Todas as views + streaming
│   ├── urls.py
│   ├── admin.py
│   └── templates/chat/
│       ├── base.html
│       ├── login.html
│       └── index.html
├── static/
│   ├── css/main.css
│   └── js/main.js
├── .env.example
├── requirements.txt
├── Procfile
├── railway.toml
└── runtime.txt
```

## Personalizar o contexto IRPF

Edite a variável `SYSTEM_PROMPT` em `chat/views.py` para adicionar:
- Regras internas do escritório
- Tabelas de valores atualizadas (ex: limites de dedução do ano vigente)
- Perguntas frequentes dos seus clientes
