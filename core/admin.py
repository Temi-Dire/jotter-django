from django.contrib import admin

from .models import EmailVerification, Post


@admin.register(Post)
class PostAdmin(admin.ModelAdmin):
    list_display = ['title', 'author', 'created_at']
    search_fields = ['title', 'body']


@admin.register(EmailVerification)
class EmailVerificationAdmin(admin.ModelAdmin):
    list_display = ['user', 'is_verified', 'code_sent_at', 'attempts']
    list_filter = ['is_verified']
    readonly_fields = ['code_hash']
