import sys
from itertools import cycle, izip
from optparse import make_option
import random

from django.contrib.auth.models import User, Permission
from django.core.management.base import NoArgsCommand
from django.db.models import Q

from challenges.models import Submission, JudgeAssignment


def count_of(thing_list, thing_name, plural_name=None, colon=False):
    """Return a string representing a count of things, given in thing_list.
    
    Example:
    
    >>> count_of([1, 2, 3], 'number')
    '3 numbers'
    >>> count_of([1], 'number')
    '1 number'
    >>> count_of(['salmon', 'carp'], 'fish', 'fishies')
    '2 fishies'
    
    """
    if plural_name is None:
        plural_name = thing_name + 's'
    format = '%d ' + (thing_name if len(thing_list) == 1 else plural_name)
    if colon:
        format += ':'
    return format % len(thing_list)


def get_judge_profiles():
    """Return the profiles of all current judges."""
    # Running this check manually because we don't want to include
    # superusers unless they've been given explicit permission
    judge_permission = Permission.objects.get(codename='judge_submission')
    judges = User.objects.filter(Q(user_permissions=judge_permission) |
                                 Q(groups__permissions=judge_permission))
    return [j.get_profile() for j in judges]


def get_submissions():
    """Return the submissions eligible for assignment."""
    is_judged = Q(judgement__isnull=False)
    is_assigned = Q(judgeassignment__isnull=False)
    
    return Submission.objects.exclude(is_judged | is_assigned)


class Command(NoArgsCommand):
    help = u'Assign unrated entries to random judges.'
    
    option_list = (NoArgsCommand.option_list +
                   (make_option('-n', '--dry-run', action='store_true',
                                help="Just print output: don't assign anything"),))
    
    def handle_noargs(self, verbosity, dry_run, **options):
        verbosity = int(verbosity)  # Django doesn't do this by default
        verbose, quiet = verbosity >= 2, verbosity < 1
        
        submissions = get_submissions()
        if not quiet:
            print count_of(submissions, 'submission',
                           colon=verbosity >= 2 and len(submissions))
            if verbose:
                for submission in submissions:
                    print '    %s' % submission.title
        
        judge_profiles = get_judge_profiles()
        if not quiet:
            print count_of(judge_profiles, 'judge',
                           colon=verbosity >= 2 and len(judge_profiles))
            if verbose:
                for judge in judge_profiles:
                    print '    %s [%s]' % (judge.display_name,
                                           judge.user.username)
        if submissions and not judge_profiles:
            print "You don't have any judges assigned"
            sys.exit(1)
        
        random.shuffle(judge_profiles)
        pairings = izip(submissions, cycle(judge_profiles))
        for submission, judge in pairings:
            if verbose:
                print '"%s" goes to %s' % \
                      (submission.title, judge.display_name)
            assignment = JudgeAssignment(submission=submission, judge=judge)
            if not dry_run:
                assignment.save()
