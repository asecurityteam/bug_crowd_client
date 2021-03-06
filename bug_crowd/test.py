import datetime
import unittest
import uuid
from unittest import mock
from urllib.parse import quote as url_quote

import requests

from .client import (
    BugcrowdClient,
    get_uri_for_bounty_submission,
    _convert_datetime_to_submission_creation_format,
)


class ClientTest(unittest.TestCase):
    """ Tests for the client module. """

    def test_get_uri_for_bounty_submission(self):
        """ tests that the get_uri_for_bounty_submission method works
            as expected.
        """
        self.client = BugcrowdClient('api-token')
        submission = get_example_submission()
        submission['bounty_code'] = '<bounty_code>'
        submission['reference_number'] = '<reference_number>'
        expected_uri = 'https://tracker.bugcrowd.com/%s/submissions/%s' % (
            url_quote(submission['bounty_code']),
            url_quote(submission['reference_number']))
        self.assertEqual(
            get_uri_for_bounty_submission(submission), expected_uri)

    def test__convert_datetime_to_submission_creation_format(self):
        date = datetime.datetime(year=2002, month=1, day=1)
        self.assertEqual(_convert_datetime_to_submission_creation_format(date),
                         date.isoformat())


class BugcrowdClientTest(unittest.TestCase):
    """ Tests for BugcrowdClient. """

    def setUp(self):
        self.api_token = 'api-token-%s' % uuid.uuid4()
        self.client = BugcrowdClient(self.api_token)
        self._bounty = get_example_bounty()

    def test_accept_header(self):
        """ tests that the accept header of the session is correct. """
        self.assertEqual(
            self.client.session.headers.get('accept'),
            'application/vnd.bugcrowd.v3+json')

    def test_get_api_uri(self):
        """ tests that the get_api_uri method works as expected. """
        path = '<eg>'
        expected = self.client.base_uri + url_quote(path)
        self.assertEqual(self.client.get_api_uri(path), expected)

    def test_get_api_uri_for_bounty_submissions(self):
        """ tests that the get_api_uri_for_bounty_submissions method works
            as expected.
        """
        expected_uri = self.client.base_uri + (
            'bounties/%s/submissions' % url_quote(self._bounty['uuid']))
        uri = self.client.get_api_uri_for_bounty_submissions(self._bounty)
        self.assertEqual(uri, expected_uri)

    def test_get_api_uri_for_submission_attachments(self):
        """ tests that the test_get_api_uri_for_submission_attachments method
            works as expected.
        """
        expected_uri = self.client.base_uri + (
            'submissions/%s/file_attachments' %
            url_quote(self._bounty['uuid']))
        uri = self.client.get_api_uri_for_submission_attachments(self._bounty)
        self.assertEqual(expected_uri, uri)

    def test_get_api_uri_for_submission(self):
        """ tests that the get_api_uri_for_submission method works
            as expected.
        """
        submission = get_example_submission()
        expected_uri = self.client.base_uri + (
            'submissions/%s' % url_quote(submission['uuid']))
        self.assertEqual(
            self.client.get_api_uri_for_submission(submission), expected_uri)

    @mock.patch.object(requests.Session, 'get')
    def test_get_bounties(self, mocked_method):
        """ tests that the get_bounties method works as expected."""
        uri = self.client.get_api_uri('bounties')
        expected_bounties = [self._bounty]
        setup_example_bounties_response(mocked_method, expected_bounties)
        self.assertEqual(self.client.get_bounties(), expected_bounties)
        mocked_method.assert_called_once_with(uri)

    @mock.patch.object(requests.Session, 'get')
    def test_get_submissions_default_params(self, mocked_method):
        """ tests that the default parameters used in the get_submissions
            method match those expected.
        """
        expected_params = {'sort': 'newest', 'offset': 0, 'limit': 250}
        setup_example_submission_response(mocked_method)
        uri = self.client.get_api_uri_for_bounty_submissions(self._bounty)
        list(self.client.get_submissions(self._bounty))
        mocked_method.assert_called_once_with(uri, params=expected_params)

    @mock.patch.object(requests.Session, 'get')
    def test_get_submissions_uses_given_params(self, mocked_method):
        """ tests that params provided to get_submissions are used. """
        expected_params = {'sort': 'newest', 'offset': 25, 'limit': 100}
        setup_example_submission_response(mocked_method)
        list(self.client.get_submissions(self._bounty, params=expected_params))
        mocked_method.assert_called_once_with(mock.ANY, params=expected_params)

    @mock.patch.object(requests.Session, 'get')
    def test_get_submissions_retrieval_one_page(self, mocked_method):
        """ tests that the get_submissions method correctly retrieves
            submissions when there is only one page of submissions.
        """
        expected_submissions = [get_example_submission()]
        content = [create_bounty_submissions_response(expected_submissions)]
        setup_mock_response(mocked_method, content)
        submissions = list(self.client.get_submissions(self._bounty))
        self.assertEqual(submissions, expected_submissions)
        mocked_method.assert_called_once_with(mock.ANY, params=mock.ANY)

    @mock.patch.object(requests.Session, 'get')
    def test_get_submissions_retrieval_no_submissions(self, mocked_method):
        """ tests that the get_submissions method correctly retrieves
            submissions when there are no submissions in a bounty program.
        """
        expected_submissions = []
        resp = create_bounty_submissions_response(expected_submissions)
        del resp['submissions']
        content = [resp]
        setup_mock_response(mocked_method, content)
        submissions = list(self.client.get_submissions(self._bounty))
        self.assertEqual(submissions, expected_submissions)

    @mock.patch.object(requests.Session, 'get')
    def test_get_submissions_retrieval_multiple_pages(self, mocked_method):
        """ tests that the get_submissions method correctly retrieves
            submissions when there are multiple pages of submissions.
        """
        num_submissions = 260
        expected_submissions = [get_example_submission(uuid=str(x))
                                for x in range(0, num_submissions)]
        json_res_one = create_bounty_submissions_response(
            expected_submissions[:-1], count=250, total_hits=num_submissions)
        json_res_two = create_bounty_submissions_response(
            expected_submissions[-1:], count=10, total_hits=num_submissions,
            offset=250)
        setup_mock_response(mocked_method, [json_res_one, json_res_two])
        submissions = list(self.client.get_submissions(self._bounty))
        self.assertEqual(submissions, expected_submissions)
        self.assertEqual(len(submissions), num_submissions)
        self.assertTrue(len(mocked_method.mock_calls) > 1)
        seen_offsets = set()
        for name, args, kwargs in mocked_method.mock_calls:
            offset = kwargs['params']['offset']
            self.assertFalse(offset in seen_offsets)
            seen_offsets.add(offset)

    @mock.patch.object(requests.Session, 'get')
    def test_get_comments_for_submission(self, mocked_method):
        """ tests that the get_comments_for_submission method works as
            expected.
        """
        submission = get_example_submission()
        uri = self.client.get_api_uri_for_submission_comments(submission)
        expected_comments = [get_example_comments()]
        setup_example_comments_response(mocked_method, expected_comments)
        self.assertEqual(self.client.get_comments_for_submission(submission),
                         expected_comments)
        mocked_method.assert_called_once_with(uri)

    @mock.patch.object(requests.Session, 'get')
    def test_get_attachments_for_submission(self, mocked_method):
        """ tests that the get_attachments_for_submission method
        works as expected.
        """
        submission = get_example_submission()
        uri = self.client.get_api_uri_for_submission_attachments(submission)
        expected_attachments = get_example_attachments()
        setup_example_comments_response(mocked_method, expected_attachments)
        self.assertEqual(self.client.
                         get_attachments_for_submission(submission),
                         expected_attachments)
        mocked_method.assert_called_once_with(uri)

    @mock.patch.object(requests.Session, 'post')
    def test_create_submission(self, mocked_method):
        """ tests that the create_submission method works as expected. """
        submitted_at = datetime.datetime(
            year=2001, month=1, day=1, minute=1, second=1)
        for submitted_at in [submitted_at, submitted_at.isoformat()]:
            fields = {'title': str(uuid.uuid4()), 'submitted_at': submitted_at}
            self.client.create_submission(self._bounty, fields)
            expected_uri = self.client.get_api_uri_for_bounty_submissions(
                self._bounty)
            if isinstance(submitted_at, datetime.datetime):
                fields.update(submitted_at=submitted_at.isoformat())
            mocked_method.assert_called_with(
                expected_uri, json={'submission': fields}, data=None)

    def test_create_submission_checks_required_fields(self):
        """ tests that the create_submission method checks that required
            fields have been supplied.
        """
        fields = {'title': 'submission without submitted_at'}
        with self.assertRaises(ValueError):
            self.client.create_submission(self._bounty, fields)

    @mock.patch.object(requests.Session, 'put')
    def test_update_submission(self, mocked_method):
        """ tests that the update_submission method works as expected. """
        fields = {'title': str(uuid.uuid4()),
                  'custom_fields': {'example': 'value'}, }
        submission = get_example_submission()
        expected_uri = self.client.get_api_uri_for_submission(submission)
        self.client.update_submission(submission, **fields)
        mocked_method.assert_called_once_with(
            expected_uri, json={'submission': fields}, data=None)

    @mock.patch.object(requests.Session, 'post')
    def test_comment_on_submission(self, mocked_method):
        """ tests that the comment_on_submission method works as expected. """
        comment_text = str(uuid.uuid4())
        expected_json = {'comment': {
            'body_markdown': comment_text, 'type': 'note', }}
        submission = get_example_submission()
        expected_uri = self.client.get_api_uri_for_submission(
            submission) + '/comments'
        self.client.comment_on_submission(submission, comment_text)
        mocked_method.assert_called_once_with(
            expected_uri, json=expected_json, data=None)

    @mock.patch.object(requests.Session, 'post')
    def test_comment_on_submission_uses_comment_type(self, mocked_method):
        """ tests that the comment_on_submission method uses the supplied
            comment type.
        """
        comment_type = 'tester_message'
        submission = get_example_submission()
        self.client.comment_on_submission(submission, 'a comment',
                                          comment_type=comment_type)
        kwargs = mocked_method.mock_calls[0][-1]
        self.assertEqual(kwargs['json']['comment']['type'], comment_type)

    @mock.patch.object(requests.Session, 'post')
    def test_transition_submission(self, mocked_method):
        """ tests that the transition_submission method works as expected. """
        expected_state = 'resolved'
        submission = get_example_submission()
        expected_uri = self.client.get_api_uri_for_submission(
            submission) + '/transition'
        self.client.transition_submission(submission, expected_state)
        mocked_method.assert_called_once_with(
            expected_uri, json={'substate': expected_state}, data=None)

    @mock.patch.object(requests.Session, 'post')
    def test_transition_submission_uses_duplicate_of(self, mocked_method):
        expected_state = 'duplicate'
        duplicate_of = 'original-%s' % uuid.uuid4()
        submission = get_example_submission()
        self.client.transition_submission(submission, expected_state,
                                          duplicate_of=duplicate_of)
        mocked_method.assert_called_once_with(
            mock.ANY, data=None,
            json={'substate': expected_state, 'duplicate_of': duplicate_of})

    @mock.patch.object(requests.Session, 'post')
    def test_transition_submission_checks_duplicate_of(self, mocked_method):
        """ tests that the transition_submission method checks that a
            duplicate_of is required for transitioning to a duplicate state.
        """
        state = 'duplicate'
        submission = get_example_submission()
        with self.assertRaises(ValueError):
            self.client.transition_submission(submission, state)


def setup_example_bounties_response(mocked_method, bounties=None):
    """ setups up an example bounties response. """
    if bounties is None:
        bounties = get_example_bounty()
    content = [create_bounty_bounties_response(bounties)]
    setup_mock_response(mocked_method, content)
    return mocked_method


def setup_example_submission_response(mocked_method):
    """ setups up an example submissions response. """
    content = [create_bounty_submissions_response([get_example_submission()])]
    setup_mock_response(mocked_method, content)
    return mocked_method


def setup_example_comments_response(mocked_method, example_comments):
    """ sets up an example comments response. """
    content = [example_comments]
    setup_mock_response(mocked_method, content)
    return mocked_method


def create_bounty_bounties_response(bounties, **kwargs):
    """ returns a submission response from the given submissions. """
    return {
        'bounties': bounties,
    }


def create_bounty_submissions_response(submissions, **kwargs):
    """ returns a submission response from the given submissions. """
    return {
        'submissions': submissions,
        'meta': {
            'count': kwargs.get('count', len(submissions)),
            'offset': kwargs.get('offset', None),
            'total_hits': kwargs.get('total_hits', len(submissions)),
        },
    }


def get_example_bounty():
    """ returns an example bounty. """
    return {
        'uuid': 'bounty-uuid-%s' % uuid.uuid4(),
        'name': 'example',
    }


def get_example_submission(**kwargs):
    """ returns an example submission. """
    return {
        'uuid': 'submission-uuid-%s' % kwargs.get('uuid', uuid.uuid4()),
        'title': 'example',
        'bounty_code': kwargs.get('bounty_code', 'code-%s' % uuid.uuid4()),
        'reference_number': kwargs.get('reference_number',
                                       'ref-n-%s' % uuid.uuid4()),
    }


def get_example_comments():
    """ returns example comments on a submission. """
    user1 = 24601
    user2 = 42
    user_ids_to_uuids = {user1: uuid.uuid4(), user2: uuid.uuid4()}
    user_ids_to_names = {user1: 'Atlassian_bot', user2: 'Cool_McJones_ASE'}
    return {'tester_messages': [
        {
            'body_markdown': 'Issue was fixed!',
            'created_at': '2018-05-08T08:33:24.732Z',
            'file_attachments_count': 0,
            'user_id': user1,
            'uuid': uuid.uuid4(),
            'identity': {
                'uuid': user_ids_to_uuids[user1],
                'name': user_ids_to_names[user1],
                'type': 'crowdcontrol_user'}
        },
        {
            'body_markdown': 'Cool! We`ve paid you.',
            'created_at': '2018-03-19T06:25:09.705Z',
            'file_attachments_count': 0,
            'user_id': user1,
            'uuid': uuid.uuid4(),
            'identity': {
                'uuid': user_ids_to_uuids[user1],
                'name': user_ids_to_names[user1],
                'type': 'crowdcontrol_user'}
        }
    ],
        'notes': [
            {
                'body_markdown': 'I verified the issue!',
                'created_at': '2018-03-15T19:54:39.714Z',
                'file_attachments_count': 0,
                'user_id': user2,
                'uuid': uuid.uuid4(),
                'identity': {
                    'uuid': user_ids_to_uuids[user2],
                    'name': user_ids_to_names[user2],
                    'type': 'bugcrowd_ase'}
            },
    ]
    }


def get_example_attachments():
    return {
        'file_attachments': [
            {
                'file_name': 'Screenshot 2020-02-04 at 20.26.57.png',
                'file_size': 817712,
                'file_type': 'image/png',
                's3_signed_url': 'https://s3.com/attachments/'
            },
            {
                'file_name': 'Screenshot 2020-02-04 at 20.43.11.png',
                'file_size': 332997,
                'file_type': 'image/png',
                's3_signed_url': 'https://s3.com/attachments/'
            },
            {
                'file_name': 'Screenshot 2020-02-04 at 20.41.44.png',
                'file_size': 719004,
                'file_type': 'image/png',
                's3_signed_url': 'https://s3.com/attachments/'
            }
        ]
    }


def setup_mock_response(mocked_method, json_contents, headers=None):
    """ setups up a mock response for testing purposes. """
    m_async_request = mock.Mock(name='async_request')
    mocked_method.return_value = m_async_request
    m_response = mock.Mock(name='response')
    m_response.json.side_effect = json_contents
    if headers is not None:
        m_response.headers = headers
    m_async_request.result.return_value = m_response
    return mocked_method


if __name__ == '__main__':
    unittest.main()
