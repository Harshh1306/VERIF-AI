from django import forms
from django.contrib.auth.forms import AuthenticationForm, UserCreationForm
from django.contrib.auth.models import User

from .models import DetectionRecord


class StyledAuthenticationForm(AuthenticationForm):
    username = forms.CharField(
        widget=forms.TextInput(attrs={'placeholder': 'Username', 'autocomplete': 'username'})
    )
    password = forms.CharField(
        widget=forms.PasswordInput(attrs={'placeholder': 'Password', 'autocomplete': 'current-password'})
    )


class SignUpForm(UserCreationForm):
    email = forms.EmailField(required=True)

    class Meta:
        model = User
        fields = ('username', 'email', 'password1', 'password2')

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['username'].widget.attrs.update({'placeholder': 'Choose a username'})
        self.fields['email'].widget.attrs.update({'placeholder': 'Email address'})
        self.fields['password1'].widget.attrs.update({'placeholder': 'Create a password'})
        self.fields['password2'].widget.attrs.update({'placeholder': 'Confirm password'})

    def clean_password1(self):
        return self.cleaned_data.get('password1')

    def _post_clean(self):
        existing_password2_errors = list(self._errors.get('password2', []))
        super()._post_clean()
        if 'password2' in self._errors:
            self._errors['password2'] = type(self._errors['password2'])(existing_password2_errors)
            if not existing_password2_errors:
                del self._errors['password2']
        if 'password1' in self._errors:
            del self._errors['password1']


class DetectionUploadForm(forms.Form):
    FILE_TYPE_CHOICES = [
        ('image', 'Image analysis'),
        ('video', 'Video analysis'),
    ]

    title = forms.CharField(
        max_length=120,
        widget=forms.TextInput(attrs={'placeholder': 'Example: Test video sample 01'}),
    )
    file_type = forms.ChoiceField(choices=FILE_TYPE_CHOICES)
    uploaded_file = forms.FileField(
        widget=forms.ClearableFileInput(
            attrs={'accept': '.jpg,.jpeg,.png,.mp4,.mov,.avi,.mkv,video/*,image/*'}
        )
    )


class DetectionRecordUpdateForm(forms.ModelForm):
    class Meta:
        model = DetectionRecord
        fields = ('title', 'notes')
        widgets = {
            'title': forms.TextInput(attrs={'placeholder': 'Report title'}),
            'notes': forms.Textarea(
                attrs={
                    'placeholder': 'Add reviewer notes, observations, or next steps',
                    'rows': 4,
                }
            ),
        }
