from django import forms
from .models import MessageTemplate

class MessageTemplateForm(forms.ModelForm):
    class Meta:
        model = MessageTemplate
        fields = ['service', 'name', 'key', 'description', 'content', 'is_active']
        widgets = {
            'description': forms.Textarea(attrs={'rows': 3}),
            "content": forms.Textarea(attrs={"rows": 16, "class": "cc-tpl-content", "spellcheck": "false"}), 
        }
