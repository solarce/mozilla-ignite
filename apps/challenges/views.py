from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.urlresolvers import reverse
from django.http import HttpResponseRedirect, Http404
from django.shortcuts import get_object_or_404
import jingo
from tower import ugettext as _

from challenges.forms import EntryForm
from challenges.models import Challenge, Phase, Submission
from projects.models import Project


def show(request, project, slug, template_name='challenges/show.html'):
    """Show an individual project challenge."""
    project = get_object_or_404(Project, slug=project)
    challenge = get_object_or_404(project.challenge_set, slug=slug)
    return jingo.render(request, template_name, {
        'challenge': challenge,
        'project': project,
        'phases': list(enumerate(challenge.phases.all(), start=1)),
        'entries': Submission.objects.filter(phase__challenge=challenge),
    })


def entries_all(request, project, slug):
    """Show all entries (submissions) to a challenge."""
    return show(request, project, slug, template_name='challenges/all.html')


@login_required
def create_entry(request, project, slug):
    project = get_object_or_404(Project, slug=project)
    
    # Quick hack to get around the current inability to obtain current phase
    try:
        phase = Phase.objects.filter(challenge__slug=slug)[0]
    except IndexError:
        raise Http404
    
    profile = request.user.get_profile()
    form_errors = False
    if request.method == 'POST':
        form = EntryForm(data=request.POST)
        if form.is_valid():
            entry = form.save(commit=False)
            entry.phase = phase
            entry.save()
            # double save needed to add in m2m key
            entry.created_by.add(profile)
            entry.save()
            msg = _('Your entry has been posted successfully and is now available for public review')
            messages.success(request, msg)
            return HttpResponseRedirect(phase.challenge.get_absolute_url())
        else:
            form_errors = {}
            # this feels horrible but I think required to create a custom error list
            for k in form.errors.keys():
                form_errors[k] =  form.errors[k].as_text()
    else:
        form = EntryForm()
    return jingo.render(request, 'challenges/create.html', {
        'project': project,
        'challenge': phase.challenge,
        'form': form,
        'errors': form_errors
    })


def entry_show(request, project, slug, entry_id):
    project = get_object_or_404(Project, slug=project)
    challenge = get_object_or_404(project.challenge_set, slug=slug)
    entry = get_object_or_404(Submission.objects, pk=entry_id,
                              phase__challenge=challenge)
    return jingo.render(request, 'challenges/show_entry.html', {
        'project': project,
        'challenge': challenge,
        'entry': entry
    })