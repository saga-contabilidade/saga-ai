from django.urls import path
from . import views

app_name = 'chat'

path('diagnostico/', views.diagnostico, name='diagnostico'),


urlpatterns = [
    path('', views.index, name='index'),
    path('login/', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),
    path('conversa/nova/', views.new_conversation, name='new_conversation'),
    path('conversa/<int:pk>/', views.conversation_detail, name='conversation'),
    path('conversa/<int:pk>/deletar/', views.delete_conversation, name='delete_conversation'),
    path('conversa/<int:pk>/mensagem/', views.send_message, name='send_message'),
    path('conversa/<int:pk>/upload/', views.upload_document, name='upload_document'),
    path('documento/<int:doc_pk>/deletar/', views.delete_document, name='delete_document'),
]
