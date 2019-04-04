from areas.models import Area
from bootstrap_modal_forms.forms import BSModalForm

class CommentModalForm(BSModalForm):
    class Meta:
        model = Area
        fields = ['title', 'description']