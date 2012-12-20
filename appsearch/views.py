## NEW
import json

from django.views.generic import View, TemplateView
from django.http import HttpResponse, HttpResponseBadRequest, HttpResponseForbidden
from django.contrib.contenttypes.models import ContentType

from appsearch.utils import Searcher
from appsearch.registry import search

class SearchMixin(object):
    context_object_name = 'search'
    form_template_name = 'appsearch/default_form.html'
    
    def get_context_object_name(self):
        return self.context_object_name
    
    def get_context_data(self, **kwargs):
        context = super(SearchMixin, self).get_context_data(**kwargs)
        object_name = self.get_context_object_name()
        context[object_name] = self.get_searcher()
        return context
    
    def get_searcher(self):
        return Searcher(self.request.path, self.request.GET, **self.get_searcher_kwargs())
    
    def get_searcher_kwargs(self):
        return {
            'form_template': self.get_form_template_name(),
            'context_object_name': self.get_context_object_name()
        }
    
    def get_context_object_name(self):
        return self.context_object_name
    
    def get_form_template_name(self):
        return self.form_template_name

class BaseSearchView(SearchMixin, TemplateView):
    pass


class BaseAjaxConfigurationResolutionView(View):
    def dispatch(self, request, *args, **kwargs):
        self.request = request
        self.args = args
        self.kwargs = kwargs
        
        model = kwargs.get('model', request.GET.get('model'))
        
        config, response = self.resolve_configuration(request, model)
        
        if config is None:
            return response
        
        self.configuration = config
        
        return super(BaseAjaxConfigurationResolutionView, self).dispatch(request, model=model)
    
    def resolve_configuration(self, request, model):
        if not request.is_ajax() and request.GET.get('ajax') != 'true':
            return None, HttpResponseBadRequest("Bad Request")
        
        if model is None:
            return None, HttpResponseBadRequest("No model is supplied")
        
        try:
            content_type = ContentType.objects.get(id=model)
        except (ValueError, ContentType.DoesNotExist):
            content_type = None
            model = None
            model_class = None
        else:
            model = '.'.join((content_type.app_label, content_type.model))
            model_class = content_type.model_class()
        
        if model_class and self.has_perm(model_class) and model in search:
            configuration = search[model]
        else:
            configuration = None
        
        if not configuration:
            return None, HttpResponseForbidden()
        
        return configuration, None
    
    def has_perm(self, model_class):
        permission = '{}.change_{}'.format(model_class._meta.app_label, model_class.__name__.lower())
        return self.request.user.has_perm(permission)
    
    
class ConstraintFieldsAjaxView(BaseAjaxConfigurationResolutionView):
    """
    Looks up a model class based on the regex parameter "model" (or from the GET data), which is a
    valid ``ContentType`` pk.
    
    """
    
    def get(self, request, *args, **kwargs):
        data = {'choices': self.configuration.get_searchable_field_choices()}
        
        return HttpResponse(json.dumps(data, indent=4), content_type='text/json')
    
class ConstraintOperatorsAjaxView(BaseAjaxConfigurationResolutionView):
    """
    Looks up a model class based on the regex parameter "model" (or from the GET data), which is a
    valid ``ContentType`` pk.
    
    """
    
    def get(self, request, *args, **kwargs):
        field = request.GET.get('field')
        
        try:
            choices = self.configuration.get_operator_choices(hash=field)
        except AttributeError:
            choices = None
        
        if not choices:
            return HttpResponseBadRequest("Bad field")
        
        data = {'choices': choices}
        
        return HttpResponse(json.dumps(data, indent=4), content_type='text/json')
    

## OLD

import datetime
import logging
import re

from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import ContentType, Permission
from django.core.exceptions import FieldError
from django.http import HttpResponseRedirect
from django.forms.formsets import formset_factory
from django.utils.decorators import method_decorator
from django.db.models import get_model, BooleanField
from django.http import HttpResponse
from django.db.models import Q    
from django.utils import simplejson as json
from django.views.generic import TemplateView
from django.contrib import messages
from django.utils.functional import curry
from django import forms

from appsearch.forms import OPERATOR_CHOICES, ConstraintForm, SearchForm
from appsearch.registry import search

log = logging.getLogger(__name__)

class Data(object):
    pass

# WORK IN PROGRESS: This assignment to "ALLOWED_MODELS" services the old implementation, making the
# new configuration structure transparent for now.
ALLOWED_MODELS = search

class AppSearch(object):    
    """ Provides Basic Functions for app search """

    def check_permissions(self,ct_list):
        """Simply verify the user has perms to view the data within the model"""
        temp_dict,model_list={},[]
        if hasattr(self.request.user, '_perm_cache'):
            app_model_list = list(self.request.user._perm_cache)
            for each_item in app_model_list:
                m = re.search(r'^(\w+).(\w+)_(\w+)', each_item)
                temp_dict[m.group(3)] = each_item

            for ct_id, model in ct_list:
                if temp_dict.get(model):
                    m = re.search(r'^(\w+).(\w+)_(\w+)', temp_dict.get(model))
                    app_label = m.group(1)
                    model_obj = get_model(app_label, model)
                    model_list.append((ct_id, model_obj._meta.verbose_name.capitalize()))
        else:
            codename_list = []
            try:
                codename_list = Permission.objects.filter(group__user=self.request.user).values_list('codename', flat=True)
            except TypeError: pass
            for codename in codename_list:
                m = re.search(r'^(\w+)_(\w+)', codename)
                temp_dict[m.group(2)]= codename

            for ct_id, model in ct_list:
                if temp_dict.get(model):
                    content_type = ContentType.objects.get( id = ct_id)
                    model_obj = get_model( content_type.app_label, content_type.model)
                    model_list.append((ct_id, model_obj._meta.verbose_name.capitalize()))
        return model_list


    def get_app_models(self):
        """ gets list of apps present in your content type """
        ct_list= list(ContentType.objects.values_list('id','model').filter(model__in=ALLOWED_MODELS.keys()))
        ct_list=self.check_permissions(ct_list)
        return ct_list
    
    def get_model_fields(self,model_id=None):
        """ gets fields inside a particular model """
        if not model_id:
            model_id  = self.request.GET.get('id')
        field_list = []
        if model_id:
            field_list=self.get_model_meta(model_id)
        return json.dumps(field_list, separators=(',',':'))
    
    def add_constraint_formset(self):
        """ add constraint formset """
        model_id,field_list = self.request.GET.get('id'), []
        if model_id:
            field_list=self.get_model_meta(model_id)
        ConstraintFormSet = formset_factory(ConstraintForm)
        formset= ConstraintFormSet(prefix="searchform")
        for form in formset:
            form.fields['filters'].choices=map(lambda x:(x[0],x[1]), field_list)
        return formset
    
    def build_query(self):
        """ prepares query for searching """
        self.natural_search_string = ''

        model, (field, operator), term = self.search_constraint[0]

        content_type = ContentType.objects.get( id = self.request.POST.get('models'))
        nss_cn = next((x[1] for x in ALLOWED_MODELS[content_type.model]['search_fields'] if x[0] == field))
        nss_cn2 = next((x[1] for x in OPERATOR_CHOICES if x[0] == operator))

        log.debug("Model: {}, Field: {}, Operator: {}, Term: {}".format(model, field, operator, term))
        if "__" not in field:
            try:
                model_field = model._meta.get_field_by_name(field)[0]
                if isinstance(model_field, BooleanField):
                    print term, type(term)
                    if term in [u'1', u'True', u'T', u'Y']:
                        operator = ""
                        term = True
                    elif term in [u'0', u'False', u'F', u'N']:
                        operator = ""
                        term = False
            except IndexError:
                log.exception("We can't find the model field {} for model {}".format(field, model))

        if operator == "__isnull":
            term = False
        elif operator == "__isnotnull":
            operator = "__isnull"
            term = True

        self.title = model._meta.verbose_name.capitalize()
        self.natural_search_string += self.title

        log.debug("Q {0}:{1}".format("".join([field, operator]), str(term)))
        query = Q(**{"".join([field, operator]): term})

        if isinstance(term, tuple):
            term = " - ".join([str(x) for x in term])
        self.natural_search_string += "s with {} {} \"{}\" ".format( nss_cn, nss_cn2, term)

        for constraint, (field, operator), term in self.search_constraint[1:]:
            try:
                nss_cn = next((x[1] for x in ALLOWED_MODELS[content_type.model]['search_fields'] if x[0] == field))
                nss_cn2 = next((x[1] for x in OPERATOR_CHOICES if x[0] == operator))
                terms = term

                if isinstance(term, tuple):
                    terms = " - ".join([str(x) for x in term])

                if "__" not in field:
                    try:
                        model_field = model._meta.get_field_by_name(field)[0]
                        if isinstance(model_field, BooleanField):
                            if term in [u'1', u'True', u'T', u'Y']:
                                operator = ""
                                term = True
                            elif term in [u'0', u'False', u'F', u'N']:
                                operator = ""
                                term = False
                    except IndexError:
                        log.exception("We can't find the model field {} for model {}".format(field, model))

                if operator == "__isnull":
                    term = False
                elif operator == "__isnotnull":
                    operator = "__isnull"
                    term = True
                if constraint == "|":
                    query|=Q(**{"".join([field, operator]): term})
                    self.natural_search_string += "or {} {} \"{}\" ".format(nss_cn, nss_cn2, terms)
                else:
                    query&=Q(**{"".join([field, operator]): term})
                    self.natural_search_string += "and {} {} \"{}\" ".format(nss_cn, nss_cn2, terms)
            except StopIteration: pass

        self.hit_query(model,query)

    def hit_query(self,model_obj,query):

        try:
            self.data_list = model_obj.objects.filter_by_user(
                self.request.user, show_attached=False).filter(query).distinct()
        except FieldError:
            try:
                self.data_list = model_obj.objects.filter_by_user(
                    self.request.user).filter(query).distinct()
            except TypeError:
                self.data_list=model_obj.objects.filter(query).distinct()

    def add_constraint(self):
        """ gets additional constraint AND/OR """
        constraint_count=self.request.POST.get('searchform-TOTAL_FORMS')
        term = self.request.POST.get('term')
        term2=self.request.POST.get('term2')
        operator=self.request.POST.get('operator')
        filters=self.request.POST.get('filters')
        if re.search('date', filters):
            try:
                term = datetime.datetime.strptime(term, '%Y-%m-%d')
            except ValueError: pass
            if term2 != u"":
                try:
                    term2 = datetime.datetime.strptime(term2, '%Y-%m-%d')
                except ValueError: pass
                term = (term, term2)

        content_type = ContentType.objects.get( id = self.request.POST.get('models') )
        model_obj = get_model( content_type.app_label, content_type.model)

        self.search_constraint = [(model_obj, (filters, operator), term)]

        for i in range(0,int(constraint_count)):
            constraint=self.request.POST.get('searchform-'+str(i)+'-constraint')
            term=self.request.POST.get('searchform-'+str(i)+'-term')
            term2=self.request.POST.get('searchform-'+str(i)+'-term2')
            operator=self.request.POST.get('searchform-'+str(i)+'-operator')
            filters=self.request.POST.get('searchform-'+str(i)+'-filters')
            if '' in [ term, operator, filters ]: continue
            if re.search('date', filters):
                try:
                    term = datetime.datetime.strptime(term, '%Y-%m-%d')
                except ValueError: pass
                if term2 != u"":
                    try:
                        term2 = datetime.datetime.strptime(term2, '%Y-%m-%d')
                    except ValueError: pass
                    term = (term, term2)
            self.search_constraint.append((constraint, (filters,operator), term))
        self.build_query()
    
    def build_data(self,model_id):
        self.field_list=self.get_model_meta(model_id,'display_fields')
        # We want the first column to if at all possible get a url to the
        # object in question.  The rest of them are values..

        urls = None
        try:
            urls = [ x.get_absolute_url() for x in self.data_list]
        except (AttributeError, Warning): pass

        self.data_list=self.data_list.values_list(*map(lambda x:x[0],self.field_list))

        if urls:
            href = '<a href="{}">{}</a>'
            results = []
            for idx,row in enumerate(self.data_list):
                row = list(row)
                row[0] = href.format(urls[idx], row[0])
                results.append(tuple(row))
            self.data_list = results

        return self.data_list


    @staticmethod         
    def get_model_all_fields( model_id ):
        
        content_type = ContentType.objects.get( id = model_id )
        model_obj = get_model( content_type.app_label, content_type.model )
        model_fields = model_obj._meta.fields
        return model_fields

    @staticmethod
    def get_model_meta( model_id,field_type='search_fields' ):
        """ takes model id as param and returns list of fileds """
        
        content_type = ContentType.objects.get( id = model_id )
        model_fields=[]
        if content_type.model in ALLOWED_MODELS.keys():
            return ALLOWED_MODELS[content_type.model][field_type]    
    
class ModelListing(TemplateView,AppSearch):
    
    template_name="appsearch/appsearch.html"

    @method_decorator(login_required)
    def dispatch(self, *args, **kwargs):
        """Ensure we have access"""
        return super(ModelListing, self).dispatch(*args, **kwargs)

    def check_valid(self):
        valid=True
        if not self.request.POST.get('models') or not self.request.POST.get('filters'):
            valid=False
            messages.error(self.request,"You haven't selected models or filter by")
        return valid
    
    def get_context_data(self,**kwargs):

        if not len(self.request.POST.keys()):
            self.form=SearchForm(self.get_app_models())
        else:
            self.form=SearchForm(self.get_app_models(), initial=self.request.POST)
        return {'form':self.form}
        
    def add_default_data(self):
        field_list=json.loads(self.get_model_fields(self.request.POST.get('models')))
        self.form.fields['filters']=forms.ChoiceField(label="Filter by",choices=field_list,initial=self.request.POST.get('filters'))
        constraint_count=self.request.POST.get('searchform-TOTAL_FORMS')
        data={'searchform-TOTAL_FORMS':constraint_count,
              'searchform-INITIAL_FORMS':self.request.POST.get('searchform-INITIAL_FORMS')}
        for i in range(0,int(constraint_count)):
            data.update({'searchform-'+str(i)+'-constraint':self.request.POST.get('searchform-'+str(i)+'-constraint'),
                        'searchform-'+str(i)+'-term':self.request.POST.get('searchform-'+str(i)+'-term'),
                        'searchform-'+str(i)+'-term2':self.request.POST.get('searchform-'+str(i)+'-term2'),
                        'searchform-'+str(i)+'-operator':self.request.POST.get('searchform-'+str(i)+'-operator'),
                        'searchform-'+str(i)+'-filters':self.request.POST.get('searchform-'+str(i)+'-filters')})
        ConstraintFormSet = formset_factory(form=ConstraintForm)
        ConstraintFormSet.form=staticmethod(curry(ConstraintForm, filters=field_list))
        self.constraint_formset= ConstraintFormSet(data,prefix="searchform")
        
    def post(self, request, *args, **kwargs):

        context = self.get_context_data(**kwargs)

        valid=self.check_valid()
        if not valid:
            return HttpResponseRedirect(self.request.META['HTTP_REFERER'])
        self.add_constraint()
        self.build_data(self.request.POST.get('models'))
        self.add_default_data()
        context.update({'data_list' : self.data_list,
                        'field_list': self.field_list,
                        'title': self.title + " Results",
                        'natural_search_string': self.natural_search_string,
                        'constraint_formset':self.constraint_formset,})
        return self.render_to_response(context)

class AjaxFillFields(TemplateView,AppSearch):

    def render_to_response(self, context, **response_kwargs):
        json_data=self.get_model_fields()
        return HttpResponse(json_data,'application/json')
        
class AjaxConstraint(TemplateView,AppSearch):

    template_name="appsearch/constraint.html"
    
    def get_context_data(self,**kwargs):
        formset=self.add_constraint_formset()
        return {'formset':formset }