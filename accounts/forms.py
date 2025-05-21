from django import forms
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.models import User
from .models import Profile

class CustomSignupForm(UserCreationForm):
    role = forms.ChoiceField(
        choices=Profile.ROLE_CHOICES,
        widget=forms.RadioSelect,
        required=True,
        label='I want to join as'
    )
    bio = forms.CharField(
        widget=forms.Textarea(attrs={'rows': 4}),
        required=False,
        label='Tell us about yourself'
    )
    
    class Meta:
        model = User
        fields = ('username', 'email', 'password1', 'password2', 'role', 'bio')
        labels = {
            'username': 'Username',
            'email': 'Email',
            'password1': 'Password',
            'password2': 'Confirm Password',
        }
    
    def save(self, commit=True):
        user = super().save(commit=False)
        user.email = self.cleaned_data['email']
        # Store the role on the user instance temporarily
        user._role = self.cleaned_data['role']
        if commit:
            user.save()
            # The profile will be created by the signal handler
            # We just need to update the bio
            profile = user.profile
            profile.bio = self.cleaned_data['bio']
            profile.save()
        return user 