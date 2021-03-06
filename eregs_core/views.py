from django.shortcuts import render, render_to_response
from django.template.loader import render_to_string
from django.http import HttpResponse, HttpResponseRedirect, Http404
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.cache import never_cache

from haystack.query import SearchQuerySet

from models import *
from utils import *
from api import *

import json
import time

from dateutil import parser as dt_parser


def regulation(request, version, eff_date, node):

    if request.method == 'GET':
        node_id = ':'.join([version, eff_date, node])
        toc_id = ':'.join([version, eff_date, 'tableOfContents'])
        meta_id = ':'.join([version, eff_date, 'preamble'])

        toc = TableOfContents.objects.get(node_id=toc_id)
        meta = Preamble.objects.get(node_id=meta_id)
        regtext = Section.objects.get(node_id=node_id)

        toc.get_descendants()
        meta.get_descendants(auto_infer_class=False)
        regtext.get_descendants()

        versions = Version.objects.exclude(version=None)
        regulations = [r for r in RegNode.objects.filter(label=meta.cfr_section, reg_version__in=versions).select_related('reg_version')]
        regulations = sorted(regulations, key=lambda x: x.version.split(':')[1], reverse=True)
        timeline = []

        preambles = Preamble.objects.filter(node_id__in=[reg.version + ':preamble' for reg in regulations]).\
            select_related('reg_version').order_by('reg_version')
        fdsys = Fdsys.objects.filter(node_id__in=[reg.version + ':fdsys' for reg in regulations]).\
            select_related('reg_version').order_by('reg_version')

        for pre, fd in zip(preambles, fdsys):
            pre.get_descendants(auto_infer_class=False)
            fd.get_descendants(auto_infer_class=False)
            timeline.append((pre, fd))

        if regtext is not None and toc is not None:
            return render_to_response('regulation.html', {'toc': toc,
                                                          'reg': regtext,
                                                          'mode': 'reg',
                                                          'meta': meta,
                                                          'timeline': timeline})


def regulation_partial(request, version, eff_date, node):

    if request.method == 'GET':
        node_id = ':'.join([version, eff_date, node])
        meta_id = ':'.join([version, eff_date, 'preamble'])

        meta = Preamble.objects.get(node_id=meta_id)
        regtext = Section.objects.get(node_id=node_id)

        meta.get_descendants(auto_infer_class=False)
        regtext.get_descendants()

        if regtext is not None and meta is not None:
            result = render_to_string('regnode.html', {'node': regtext,
                                                       'mode': 'reg',
                                                       'meta': meta})
            result = '<section id="content-wrapper" class="reg-text">' + result + '</section>'
            return HttpResponse(result)


def sidebar_partial(request, version, eff_date, node):

    if request.method == 'GET':
        node_id = ':'.join([version, eff_date, node])
        meta_id = ':'.join([version, eff_date, 'preamble'])

        meta = Preamble.objects.get(node_id=meta_id)
        regtext = Section.objects.get(node_id=node_id)

        meta.get_descendants(auto_infer_class=False)
        regtext.get_descendants()

        if regtext is not None:
            return render_to_response('right_sidebar.html', {'node': regtext,
                                                             'mode': 'reg',
                                                             'meta': meta})


def definition_partial(request, version, eff_date, node):

    if request.method == 'GET':
        node_id = ':'.join([version, eff_date, node])
        regtext = Paragraph.objects.get(node_id=node_id)
        regtext.get_descendants()

        if regtext is not None:
            return render_to_response('definition.html', {'node': regtext,
                                                          'mode': 'reg'})


def sxs_partial(request, version, eff_date, node):

    if request.method == 'GET':
        node_id = ':'.join([version, eff_date, node])
        meta_id = ':'.join([version, eff_date, 'preamble'])

        meta = Preamble.objects.get(node_id=meta_id)
        regtext = Section.objects.get(node_id=node_id)

        meta.get_descendants(auto_infer_class=False)
        regtext.get_analysis()

        footnotes = [elem for child in regtext.analysis[0].children if child.tag == 'analysisParagraph'
                     for elem in child.children if elem.tag == 'footnote']

        if regtext is not None:
            return render_to_response('sxs.html', {'node': regtext,
                                                   'footnotes': footnotes,
                                                   'mode': 'reg'})


def diff_redirect(request, left_version, left_eff_date):

    if request.method == 'GET':
        new_version = request.GET['new_version']
        right_version = new_version.split(':')
        print left_version, left_eff_date, new_version
        version = Version.objects.get(left_version=':'.join([left_version, left_eff_date]),
                                      right_version=new_version)
        sections = Section.objects.filter(reg_version=version,
                                          tag='section').exclude(label='').order_by('label')
        first_section = sections[0]
        print first_section
        return HttpResponseRedirect('/diff/{}/{}/{}/{}/{}'.format(
            left_version, left_eff_date, right_version[0], right_version[1], first_section.label
        ))


def diff(request, left_version, left_eff_date, right_version, right_eff_date, node):

    if request.method == 'GET':
        node_id = ':'.join([left_version, left_eff_date, right_version, right_eff_date, node])
        toc_id = ':'.join([left_version, left_eff_date, right_version, right_eff_date, 'tableOfContents'])
        meta_id = ':'.join([left_version, left_eff_date, right_version, right_eff_date, 'preamble'])

        toc = DiffNode.objects.get(node_id=toc_id)
        meta = DiffNode.objects.get(node_id=meta_id)
        regtext = DiffNode.objects.get(node_id=node_id)

        toc.get_descendants(desc_type=DiffNode)
        meta.get_descendants(desc_type=DiffNode)
        regtext.get_descendants(desc_type=DiffNode)

        toc.__class__ = TableOfContents
        meta.__class__ = DiffPreamble
        regtext.__class__ = Section

        versions = Version.objects.exclude(version=None)
        regulations = [r for r in RegNode.objects.filter(label=meta.cfr_section, reg_version__in=versions).select_related('reg_version')]
        regulations = sorted(regulations, key=lambda x: x.version.split(':')[1], reverse=True)
        timeline = []

        preambles = Preamble.objects.filter(node_id__in=[reg.version + ':preamble' for reg in regulations]).\
            select_related('reg_version').order_by('reg_version')
        fdsys = Fdsys.objects.filter(node_id__in=[reg.version + ':fdsys' for reg in regulations]).\
            select_related('reg_version').order_by('reg_version')

        print meta.left_version, meta.right_version
        for pre, fd in zip(preambles, fdsys):
            pre.get_descendants(auto_infer_class=False)
            fd.get_descendants(auto_infer_class=False)
            timeline.append((pre, fd))
            print pre.version


        if regtext is not None and toc is not None:
            return render_to_response('regulation.html', {'toc': toc,
                                                          'reg': regtext,
                                                          'mode': 'diff',
                                                          'meta': meta,
                                                          'timeline': timeline})

@never_cache
def search_partial(request):

    if request.method == 'GET':

        results = get_search_results(request)
        return render_to_response('search_results.html', results)

@never_cache
def search(request):

    if request.method == 'GET':
        version = request.GET['version']
        results = get_search_results(request)
        toc_id = ':'.join([version, 'tableOfContents'])
        meta_id = ':'.join([version, 'preamble'])

        toc = TableOfContents.objects.get(node_id=toc_id)
        meta = Preamble.objects.get(node_id=meta_id)

        toc.get_descendants()
        meta.get_descendants(auto_infer_class=False)

        versions = Version.objects.exclude(version=None)
        regulations = [r for r in RegNode.objects.filter(label=meta.cfr_section, reg_version__in=versions).select_related('reg_version')]
        regulations = sorted(regulations, key=lambda x: x.version.split(':')[1], reverse=True)
        timeline = []

        preambles = Preamble.objects.filter(node_id__in=[reg.version + ':preamble' for reg in regulations]).\
            select_related('reg_version').order_by('reg_version')
        fdsys = Fdsys.objects.filter(node_id__in=[reg.version + ':fdsys' for reg in regulations]).\
            select_related('reg_version').order_by('reg_version')

        for pre, fd in zip(preambles, fdsys):
            pre.get_descendants(auto_infer_class=False)
            fd.get_descendants(auto_infer_class=False)
            timeline.append((pre, fd))

        results['toc'] = toc
        results['mode'] = 'search'
        results['meta'] = meta
        results['timeline'] = timeline

        return render_to_response('regulation.html', results)


def get_search_results(request):

    q = request.GET['q']
    q_version = request.GET['version']
    version = Version.objects.get(version=q_version)
    page = int(request.GET.get('page', 1)) - 1

    results = SearchQuerySet().filter(content=q, version__exact=q_version)
    view_results = results[page * 10: page * 10 + 10]

    result_nodes = []

    for r in view_results:
        ancestors = r.object.get_ancestors()[::-1]
        for ancestor in ancestors:
            if ancestor.tag in ['paragraph', 'interpParagraph'] and r.text is not None and not r.text.strip == ''\
                    and len(r.version.split(':')) == 2:
                ancestor.get_descendants()
                result_nodes.append((ancestor, r.text))
                break

    page += 1

    if page == 1:
        prev_page = None
    else:
        prev_page = page - 1

    rem = len(results) % 10
    total_pages = len(results) // 10 + rem // 10

    if page >= total_pages:
        next_page = None
    else:
        next_page = page + 1

    if total_pages == 0:
        total_pages = 1

    return {'results': result_nodes,
            'search_term': q,
            'version': version,
            'total_pages': total_pages,
            'page': page,
            'prev_page': prev_page,
            'next_page': next_page}


def regulation_main(request, part_number):

    if request.method == 'GET':

        non_blank_versions = Version.objects.exclude(version=None)
        regulations = [r for r in RegNode.objects.filter(label=part_number, reg_version__in=non_blank_versions)]
        for r in regulations:
            print r.reg_version.id, r.reg_version
        regulations = sorted(regulations, key=lambda x: x.version.split(':')[1], reverse=True)

        most_recent_reg = regulations[0]
        toc_id = most_recent_reg.version + ':tableOfContents'
        meta_id = most_recent_reg.version + ':preamble'

        toc = TableOfContents.objects.get(node_id=toc_id)
        meta = Preamble.objects.get(node_id=meta_id)

        toc.get_descendants()
        meta.get_descendants(auto_infer_class=False)

        timeline = []

        for reg in regulations:
            preamble = Preamble.objects.filter(node_id=reg.version + ':preamble').order_by('reg_version')
            fdsys = Fdsys.objects.filter(node_id=reg.version + ':fdsys').order_by('reg_version')
            for pre, fd in zip(preamble, fdsys):
                pre.get_descendants(auto_infer_class=False)
                fd.get_descendants(auto_infer_class=False)
                timeline.append((pre, fd))

        landing_page = 'landing_pages/reg_{}.html'.format(meta.cfr_section)
        landing_page_sidebar = 'landing_pages/reg_{}_sidebar.html'.format(meta.cfr_section)

        if toc is not None and meta is not None:
            return render_to_response('regulation.html', {'toc': toc,
                                                          'meta': meta,
                                                          'timeline': timeline,
                                                          'mode': 'landing',
                                                          'landing_page': landing_page,
                                                          'landing_page_sidebar': landing_page_sidebar})


def main(request):

    if request.method == 'GET':

        # meta = Preamble.objects.filter(tag='preamble')
        reg_versions = Version.objects.exclude(version=None)
        meta = [r for r in Preamble.objects.filter(tag='preamble', reg_version__in=reg_versions)]
        # meta = sorted(meta, key=lambda x: x.reg_letter, reverse=True)

        regs_meta = []
        reg_parts = set()

        for item in meta:
            item.get_descendants(auto_infer_class=False)
            if item.reg_letter not in reg_parts:
                regs_meta.append(item)
                reg_parts.add(item.reg_letter)

        regs_meta = sorted(regs_meta, key=lambda x: int(x.cfr_section))
        print [(item.reg_letter, item.node_id) for item in regs_meta]
        fdsys = RegNode.objects.filter(tag='fdsys')

        return render_to_response('main.html', {'preamble': regs_meta,
                                                'fdsys': fdsys})
