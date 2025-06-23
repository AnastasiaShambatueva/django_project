from django.contrib import admin
from .models import Article


@admin.register(Article)
class ArticleAdmin(admin.ModelAdmin):
    # Настройка отображения списка
    list_display = ('title', 'published_at', 'is_published')
    list_editable = ('is_published',)  # Поля для быстрого редактирования

    # Фильтры и поиск
    list_filter = ('is_published', 'published_at')
    search_fields = ('title', 'content')

    # Настройка формы редактирования
    fieldsets = (
        ('Основное', {
            'fields': ('title', 'content')
        }),
        ('Дополнительно', {
            'fields': ('is_published',),
            'classes': ('collapse',)  # Сворачиваемая секция
        }),
    )