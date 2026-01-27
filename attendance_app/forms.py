from django import forms
from django.contrib.auth import get_user_model
from .models import TeacherProfile, SchoolSettings, AcademicYear

User = get_user_model()



class TeacherProfileForm(forms.ModelForm):
    username = forms.CharField(
        max_length=150,
        widget=forms.TextInput(attrs={'class': 'form-control'})
    )
    email = forms.EmailField(
        required=True,
        widget=forms.EmailInput(attrs={'class': 'form-control'})
    )

    class Meta:
        model = TeacherProfile
        fields = ['profile_picture']  # only profile picture from TeacherProfile
        widgets = {
            'profile_picture': forms.ClearableFileInput(attrs={'class': 'form-control'})
        }

    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)
        if self.user:
            self.fields['username'].initial = self.user.username
            self.fields['email'].initial = self.user.email

    def save(self, commit=True):
        # Update user
        if self.user:
            self.user.username = self.cleaned_data.get('username', self.user.username)
            self.user.email = self.cleaned_data.get('email', self.user.email)
            if commit:
                self.user.save()

        # Update profile picture only
        profile = super().save(commit=False)
        if commit:
            profile.user = self.user
            profile.save()

        return profile


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
