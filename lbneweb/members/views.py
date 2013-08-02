from django.shortcuts import render
from django.views import generic
from django.db.models import Q

from members.models import Individual, Institution, Role
from members.forms import SearchMemberListForm


class IndexView(generic.ListView):
    model = Individual
    template_name = 'index_list.html'
    context_object_name = 'data'

    def get_queryset(self):
        'Return what this lists'
        member_list = Individual.objects.select_related().filter(collaborator=True)

        return dict(member_list = member_list,
                    count = len(member_list),
                    instCount = len(set(member_list.values_list('institution'))),
                    institution = None, # later
                    form = None,        # later
                )
        
        
class CollaboratorView(generic.DetailView):
    model = Individual
    template_name = 'collaborator.html'
    context_object_name = 'member'


class InstitutionView(generic.DetailView):
    model = Institution
    template_name = 'institution.html'
    context_object_name = 'member'

class RoleView(generic.DetailView):
    model = Role
    template_name = 'role.html'
    context_object_name = 'member'

def search(request):
    member_list = Individual.objects.select_related().filter(collaborator=True)
    
    # search form
    from members.forms import SearchMemberListForm
    if request.method == 'POST':
        form = SearchMemberListForm(request.POST) # bound form
        if form.is_valid():
            if not form.cleaned_data['institution'] == 'All':
                member_list = member_list.filter(institution__short_name=form.cleaned_data['institution'])
            if not form.cleaned_data['role'] == 'All':
                member_list = member_list.filter(role__name=form.cleaned_data['role'])
            if form.cleaned_data['name']:
                name = form.cleaned_data['name']
                member_list = member_list.filter( Q(last_name__icontains=name) 
                    | Q(first_name__icontains=name))          
        else:
            member_list = member_list.filter(id=0) # hack, no match

    else:
        form = SearchMemberListForm() # unbound form

    return render(request, 'index_list.html', 
                  dict(form=form, institution = None,
                       member_list = member_list,
                       instCount = len(set(member_list.values_list('institution'))),
                       count = member_list.count(),))


class SearchView(generic.edit.FormView):
    template_name = 'search.html'
    form_class = SearchMemberListForm
    success_url = '/'
    
    def form_valid(self, form):
        return super(SearchView, self).form_valid(form)

from django.http import HttpResponse
def xls_to_response(xls, fname):
    response = HttpResponse(mimetype="application/ms-excel")
    response['Content-Disposition'] = 'attachment; filename=%s' % fname
    xls.save(response)
    return response

from django.core import serializers
def members_to_xls(member_list):
    import xlwt
    wb = xlwt.Workbook()
    ws = wb.add_sheet('Collaborators')

    members = serializers.serialize( "python", member_list)
    for irow,mem in enumerate(members):
        if irow == 0:
            for icol, name in enumerate(mem['fields'].keys()):
                ws.write(irow, icol, name)
        irow += 1
        for icol, value in enumerate(mem['fields'].values()):
            ws.write(irow, icol, str(value))
    return wb


import os
from latexer import process_latex
def latex_response(pdffile, context):
    print pdffile
    texfile = os.path.splitext(pdffile)[0]+'.tex'
    pdf = process_latex(texfile, context)
    response = HttpResponse(mimetype="application/pdf")
    response['Content-Disposition'] = 'attachment; filename=%s' % pdffile
    response.write(pdf)
    return response


def inst_name_order(inst):
    name = inst.full_name.upper()
    if name.startswith('UNIV. OF '):
        return name[len('UNIV. OF '):]
    return name

def export(request, filename):
    if not filename:
        filename = 'export.html'
    member_list = Individual.objects.select_related().filter(collaborator=True)
    inst_list = sorted(set([m.institution for m in member_list]), key=inst_name_order)
    context = dict(inst_list = inst_list, member_list = member_list)

    if filename.endswith('.xls'):
        wb = members_to_xls(member_list) # fixme: pass context
        return xls_to_response(wb, filename)

    if filename.endswith('.pdf'):
        return latex_response(filename, context)

    content_type = 'text/html'
    if filename.endswith('.tex'):
        content_type = 'text/plain'
    if filename.endswith('.txt'):
        content_type = 'text/plain'

    return render(request, filename, context,
                  content_type = content_type)
    
