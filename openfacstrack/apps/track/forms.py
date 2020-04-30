from django import forms


class ConfirmFileForm(forms.Form):
    file_id = forms.CharField(max_length=255)
