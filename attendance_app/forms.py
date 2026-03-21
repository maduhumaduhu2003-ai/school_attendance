from django import forms
from django.contrib.auth import get_user_model
from .models import TeacherProfile, SchoolSettings, AcademicYear


User = get_user_model()



class SchoolSettingsForm(forms.ModelForm):
    class Meta:
        model = SchoolSettings
        fields = ['school_name', 'logo']
        widgets = {
            'school_name': forms.TextInput(attrs={'class': 'form-control'}),
        }


class UserUpdateForm(forms.ModelForm):
    class Meta:
        model = User
        fields = ['first_name', 'last_name', 'email']
        widgets = {
            'first_name': forms.TextInput(attrs={'class': 'form-control'}),
            'last_name': forms.TextInput(attrs={'class': 'form-control'}),
            'email': forms.EmailInput(attrs={'class': 'form-control'}),
        }


class AcademicYearForm(forms.ModelForm):
    class Meta:
        model = AcademicYear
        fields = ['year_start', 'year_end', 'is_active']
        widgets = {
            'year_start': forms.NumberInput(attrs={'class': 'form-control', 'placeholder': 'Start Year'}),
            'year_end': forms.NumberInput(attrs={'class': 'form-control', 'placeholder': 'End Year'}),
            'is_active': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }
