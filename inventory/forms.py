from django import forms
from .models import Item, CustomField, CustomFieldValue

class ItemForm(forms.ModelForm):
    class Meta:
        model = Item
        fields = ['name', 'description', 'category', 'department', 'serial_no', 'quantity', 'status', 
                  'location', 'person_accountable', 'image', 'acquisition_date', 
                  'end_of_life_date', 'acquisition_cost']
        widgets = {
            'acquisition_date': forms.DateInput(attrs={'type': 'date'}),
            'end_of_life_date': forms.DateInput(attrs={'type': 'date'}),
            'description': forms.Textarea(attrs={'rows': 3}),
            'quantity': forms.NumberInput(attrs={'min': 1, 'value': 1}),
            'acquisition_cost': forms.NumberInput(attrs={'step': '0.01', 'placeholder': '0.00'}),
            'serial_no': forms.TextInput(attrs={'placeholder': 'e.g., SN123456789'}),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Add custom field widgets dynamically
        for custom_field in CustomField.objects.filter(is_active=True):
            field_name = f'custom_{custom_field.id}'
            required = custom_field.is_required
            
            if custom_field.field_type == 'text':
                self.fields[field_name] = forms.CharField(
                    required=required,
                    label=custom_field.name,
                    help_text=custom_field.help_text,
                    widget=forms.TextInput(attrs={'placeholder': custom_field.placeholder, 'class': 'form-control'})
                )
            elif custom_field.field_type == 'textarea':
                self.fields[field_name] = forms.CharField(
                    required=required,
                    label=custom_field.name,
                    help_text=custom_field.help_text,
                    widget=forms.Textarea(attrs={'placeholder': custom_field.placeholder, 'rows': 3, 'class': 'form-control'})
                )
            elif custom_field.field_type == 'number':
                self.fields[field_name] = forms.FloatField(
                    required=required,
                    label=custom_field.name,
                    help_text=custom_field.help_text,
                    widget=forms.NumberInput(attrs={'placeholder': custom_field.placeholder, 'class': 'form-control'})
                )
            elif custom_field.field_type == 'date':
                self.fields[field_name] = forms.DateField(
                    required=required,
                    label=custom_field.name,
                    help_text=custom_field.help_text,
                    widget=forms.DateInput(attrs={'type': 'date', 'class': 'form-control'})
                )
            elif custom_field.field_type == 'boolean':
                self.fields[field_name] = forms.BooleanField(
                    required=False,
                    label=custom_field.name,
                    help_text=custom_field.help_text,
                    widget=forms.CheckboxInput(attrs={'class': 'form-check-input'})
                )
            elif custom_field.field_type == 'url':
                self.fields[field_name] = forms.URLField(
                    required=required,
                    label=custom_field.name,
                    help_text=custom_field.help_text,
                    widget=forms.URLInput(attrs={'placeholder': custom_field.placeholder, 'class': 'form-control'})
                )
            elif custom_field.field_type == 'email':
                self.fields[field_name] = forms.EmailField(
                    required=required,
                    label=custom_field.name,
                    help_text=custom_field.help_text,
                    widget=forms.EmailInput(attrs={'placeholder': custom_field.placeholder, 'class': 'form-control'})
                )
            
            # Populate existing value if editing
            if self.instance and self.instance.pk:
                try:
                    custom_value = CustomFieldValue.objects.get(item=self.instance, field=custom_field)
                    if custom_field.field_type == 'boolean':
                        self.initial[field_name] = custom_value.value_boolean
                    elif custom_field.field_type == 'date':
                        self.initial[field_name] = custom_value.value_date
                    elif custom_field.field_type == 'number':
                        self.initial[field_name] = custom_value.value_number
                    else:
                        self.initial[field_name] = custom_value.value_text
                except CustomFieldValue.DoesNotExist:
                    pass