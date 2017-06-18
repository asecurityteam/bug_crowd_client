from requests_futures.sessions import FuturesSession
import six
from six.moves.urllib.parse import quote as url_quote


def _get_uuid(obj):
    """ returns the uuid of a bounty or submission object. """
    if isinstance(obj, six.string_types):
        return obj
    return obj['uuid']


class BugcrowdClient(object):

    def __init__(self, api_token, **kwargs):
        """ Creates a Bugcrowd api client. """
        self._api_token = api_token
        self.session = FuturesSession(max_workers=5)
        self.base_uri = 'https://api.bugcrowd.com/'
        self.session.headers.update({
            'Accept': 'application/vnd.bugcrowd.v2+json',
            'Authorization': 'Token %s' % self._api_token,
            'user-agent': 'Bugcrowd Python Client',
        })

    def get_bounties(self):
        """ Returns bounties. """
        resp = self.session.get(self.get_api_uri('bounties')).result()
        resp.raise_for_status()
        return resp.json()['bounties']

    def get_submissions(self, bounty, **kwargs):
        """ Yields submissions for the given bounty or bounty uuid.
            By providing a params parameter submissions can be filtered
            as per https://docs.bugcrowd.com/v1.0/docs/submission .
        """
        params = kwargs.get('params', None)
        submissions_uri = self.get_api_uri_for_bounty_submissions(bounty)
        submissions = []
        step = 25
        if params is None:
            params = {'sort': 'newest', 'offset': 0}
        initial_response = self.session.get(
            submissions_uri, params=params).result()
        initial_response.raise_for_status()
        data = initial_response.json()
        submissions += data['submissions']
        total = data['meta']['count']
        total_hits = data['meta']['total_hits']
        for submission in submissions:
            yield submission
        if total < total_hits:
            async_fetches = []
            for offset in range(step, total_hits, step):
                request_params = params.copy()
                request_params.update({'offset': offset})
                async_fetches.append(
                    self.session.get(submissions_uri, params=request_params))
            for future_fetch in async_fetches:
                fetch = future_fetch.result()
                fetch.raise_for_status()
                data = fetch.json()
                for submission in data['submissions']:
                    yield submission

    def get_api_uri(self, path):
        """ Returns the full api uri for the given path. """
        return self.base_uri + url_quote(path)

    def get_api_uri_for_bounty_submissions(self, bounty):
        """ Returns the submissions uri for the provided bounty
            or bounty uuid.
        """
        bounty_uuid = _get_uuid(bounty)
        return self.get_api_uri('bounties/%s/submissions' % bounty_uuid)

    def get_api_uri_for_submission(self, submission):
        """ Returns the uri for the given submission or submission uuid. """
        submission_uuid = _get_uuid(submission)
        return self.get_api_uri('submissions/%s' % submission_uuid)

    def create_submission(self, bounty, submission_fields):
        """ Returns a future request creating a submission in the
            given bounty or bounty uuid.
        """
        uri = self.get_api_uri_for_bounty_submissions(_get_uuid(bounty))
        required_fields = {'title', 'submitted_at'}
        has_req_fields = required_fields & set(submission_fields.keys())
        if len(has_req_fields) != 2:
            raise ValueError('The %s field is required' %
                             (required_fields - has_req_fields))
        submitted_at = submission_fields['submitted_at']
        if hasattr(submitted_at, 'isoformat'):
            submission_fields = submission_fields.copy()
            submission_fields['submitted_at'] = submitted_at.isoformat()
        return self.session.post(uri, json={'submission': submission_fields})

    def update_submission(self, submission, **kwargs):
        """ Returns a future request updating the given submission. """
        uri = self.get_api_uri_for_submission(submission)
        fields = {}
        for key in ['title', 'internal_bug_type', 'custom_fields']:
            val = kwargs.get(key, None)
            if val:
                fields[key] = val
        payload = {'submission': fields}
        return self.session.put(uri, json=payload)

    def comment_on_submission(self, submission, comment_text,
                              comment_type='note'):
        """ Returns a future request commenting on the given submission. """
        uri = self.get_api_uri_for_submission(submission) + '/comments'
        payload = {
            'comment': {
                'body': comment_text,
                'type': comment_type,
            }
        }
        return self.session.post(uri, json=payload)

    def transition_submission(self, submission, state, **kwargs):
        """ Returns a future request transition the given
            submission or submission uuid to a different state.
        """
        uri = self.get_api_uri_for_submission(submission) + '/transition'
        payload = {'substate': state}
        duplicate_of = kwargs.get('duplicate_of', None)
        if duplicate_of:
            payload['duplicate_of'] = duplicate_of
        if state == 'duplicate' and duplicate_of is None:
            raise ValueError(
                'The duplicate_of field is required when transitioning '
                'a submission to a duplicate status.')
        return self.session.post(uri, json=payload)


def _convert_datetime_to_submission_creation_format(date_time):
    return date_time.isoformat()


def get_uri_for_bounty_submission(submission):
    """ returns the uri for a given bounty submission. """
    return 'https://tracker.bugcrowd.com/%s/submissions/%s' % (
        url_quote(submission['bounty_code']),
        url_quote(submission['reference_number'])
    )
