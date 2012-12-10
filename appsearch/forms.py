from django import forms

OPERATOR_CHOICES = [
    ("__lt", "<"),
    ("__gt", ">"),
    ("__iexact", "=="),
    ('__icontains', "contains"),
    ('__range', "range of" ),
    ('__isnull', "Exists" ),
    ('__isnotnull', "Not Exists" ),
]

class SearchForm(forms.Form):
    """ initial form with models list for appsearch """
    models = forms.ChoiceField(label="Search For")
    filters = forms.ChoiceField(label="Filter by", choices=[])
    operator = forms.ChoiceField(label="Constraint Type", choices=OPERATOR_CHOICES)
    term = forms.CharField(label="Search Term")
    term2 = forms.CharField(label="End Search Term")
    
    def __init__(self, model_list, *args, **kwargs):
        super(SearchForm, self).__init__(*args, **kwargs)
        temp_list= [('','Search For')]
        temp_list.extend(model_list)
        self.fields['models'].choices = temp_list
        self.fields['operator'].initial = "__icontains"

class ConstraintForm(forms.Form):
    """ form adds up constraints along with initial form """   
    
    constraint   =   forms.ChoiceField(label="Add Constraint",choices=[('&', 'AND'),('|','OR')])
    filters      =   forms.ChoiceField(label="Filter By",choices=[])
    operator     =   forms.ChoiceField(label="Constraint Type", choices=OPERATOR_CHOICES)
    term         =   forms.CharField(label="Search Term")
    term2        =   forms.CharField(label="End Term")

    def __init__(self,filters=None, *args, **kwargs):
        super(ConstraintForm, self).__init__(*args, **kwargs)
        self.fields['operator'].initial = 5
        if filters:
            self.fields['filters'].choices = filters
