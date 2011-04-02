from django.contrib.auth.decorators import login_required
from django.db.models import Max
from django.http import HttpResponse, HttpResponseNotAllowed
from django.shortcuts import get_object_or_404, redirect
from django.template.loader import render_to_string
from django.views.generic.list_detail import object_list, object_detail

from spider.commands import run_spider
from spider.models import SpiderProfile, SpiderSession, URLResult

from djutils.utils.http import json_response


def profile_list(request, template_name='spider/profile_list.html'):
    queryset = SpiderProfile.objects.all()
    return object_list(
        request,
        queryset=queryset,
        template_name=template_name,
        paginate_by=20,
        page=int(request.GET.get('page', 1)),
    )

def profile_detail(request, profile_id, template_name='spider/profile_detail.html'):
    profile = get_object_or_404(SpiderProfile, pk=profile_id)
    queryset = profile.sessions.all()
    return object_list(
        request,
        queryset=queryset,
        template_name=template_name,
        paginate_by=20,
        page=int(request.GET.get('page', 1)),
        extra_context={'profile': profile},
    )

def session_detail(request, profile_id, session_id, template_name='spider/session_detail.html'):
    profile = get_object_or_404(SpiderProfile, pk=profile_id)
    session = get_object_or_404(profile.sessions.all(), pk=session_id)
    queryset = session.results.all().order_by('-pk')
    
    max_id = queryset.aggregate(max_id=Max('id'))['max_id'] or 0
    
    if request.is_ajax():
        max_id = int(request.GET.get('max_id', max_id))
        context = {'max_id': max_id, 'complete': session.complete, 'results': []}
        
        results = queryset.filter(pk__gt=max_id).order_by('-id')
        
        if results:
            context['max_id'] = results[0].pk
            context['results'] = [
                render_to_string('spider/includes/result_list.html', {'object': r}) \
                    for r in results
            ]
        
        return json_response(context)
    else:
        ordering = request.GET.get('ordering', '').lstrip('-')
        if ordering in ('response_time', 'content_length', 'url'):
            queryset = queryset.order_by(request.GET['ordering'])
        
        return object_list(
            request,
            queryset=queryset,
            template_name=template_name,
            paginate_by=50,
            page=int(request.GET.get('page', 1)),
            extra_context={
                'session': session,
                'max_id': max_id,
            }
        )

@login_required
def session_create(request, profile_id):
    if request.method != 'POST':
        return HttpResponseNotAllowed()

    profile = get_object_or_404(SpiderProfile, pk=profile_id)
    
    new_session = SpiderSession.objects.create(spider_profile=profile)
    run_spider(new_session.pk)
    
    if request.is_ajax():
        return json_response({'id': new_session.pk})
    
    return redirect(new_session)

def url_result_detail(request, profile_id, session_id, url_result_id,
        template_name='spider/url_result_detail.html'):
    profile = get_object_or_404(SpiderProfile, pk=profile_id)
    session = get_object_or_404(profile.sessions.all(), pk=session_id)
    
    if request.is_ajax():
        result = get_object_or_404(session.results.all(), pk=url_result_id)
        context = {
            'rendered': render_to_string('spider/includes/result_detail.html', {'object': result})
        }
        return json_response(context)
    else:
        return object_detail(
            request,
            queryset=session.results.all(),
            object_id=url_result_id,
            template_name=template_name,
            extra_context={
                'profile': profile,
                'sessoin': session,
            }
        )
