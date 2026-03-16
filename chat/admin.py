from django.contrib import admin
from .models import Conversation, Message, UploadedDocument


class MessageInline(admin.TabularInline):
    model = Message
    extra = 0
    readonly_fields = ('role', 'content', 'created_at')
    can_delete = False

class DocumentInline(admin.TabularInline):
    model = UploadedDocument
    extra = 0
    readonly_fields = ('original_name', 'uploaded_at')


@admin.register(Conversation)
class ConversationAdmin(admin.ModelAdmin):
    list_display = ('title', 'user', 'created_at', 'updated_at')
    list_filter = ('user',)
    inlines = [MessageInline, DocumentInline]


@admin.register(UploadedDocument)
class UploadedDocumentAdmin(admin.ModelAdmin):
    list_display = ('original_name', 'user', 'uploaded_at')
    list_filter = ('user',)


admin.site.site_header = 'IRPF Chat — Administração'
admin.site.site_title = 'IRPF Chat'
