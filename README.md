# Bugcrowd api client.
[![pypi-version-image]][pypi]


This package provides an implementation of the [Bugcrowd api](https://docs.bugcrowd.com/v1.0/docs/bounty).

----

## Installation
To install simply run
```
pip install bug-crowd-api-client
```

## Using this library

##### To create a Bugcrowd client

```python
    from bug_crowd.client import BugcrowdClient
    client = BugcrowdClient('API_TOKEN')
```

##### To get bug bounties

```python
    from bug_crowd.client import BugcrowdClient
    client = BugcrowdClient('API_TOKEN')
    bounties = client.get_bounties()
```

##### To get submissions for a bug bounty

```python
    from bug_crowd.client import BugcrowdClient
    client = BugcrowdClient('API_TOKEN')
    bounty = client.get_bounties()[0]
    submissions = list(client.get_submissions(bounty))
```

##### To create a bug bounty submission

```python
    import datetime

    from bug_crowd.client import BugcrowdClient
    client = BugcrowdClient('API_TOKEN')
    bounty = client.get_bounties()[0]
    submission_fields = {
        'substate': 'unresolved',
        'title': 'Example submission',
        'submitted_at': '11-11-2017 00:00:00',
        'description_markdown': 'Example description',
    }

    resp = client.create_submission(bounty, submission_fields).result()
    resp.raise_for_status()
    submission = resp.json()
```

#####  To update a bug bounty submission

```python
    from bug_crowd.client import BugcrowdClient
    client = BugcrowdClient('API_TOKEN')
    bounty = client.get_bounties()[0]
    submission = client.get_submissions(bounty)[0]

    resp = client.update_submission(
        submission,
        title='A new title',
        internal_bug_type='xss',
        custom_fields={'example': 'value'},
    ).result()
    resp.raise_for_status()
    updated_submission = resp.json()
```

#####  To comment on a bug bounty submission

```python
    from bug_crowd.client import BugcrowdClient
    client = BugcrowdClient('API_TOKEN')
    bounty = client.get_bounties()[0]
    submission = client.get_submissions(bounty)[0]

    resp = client.comment_on_submission(
        submission,
        'A comment',
        comment_type='tester_message',
    ).result()
    resp.raise_for_status()
    comment = resp.json()
```

##### To transition a bug bounty submission to a status

```python
    from bug_crowd.client import BugcrowdClient

    client = BugcrowdClient('API_TOKEN')
    bounty = client.get_bounties()[0]
    submission = client.get_submissions(bounty)[0]

    resp = client.transition_submission(
        submission,
        'triaged',
    ).result()
    resp.raise_for_status()
```


[pypi-version-image]: https://img.shields.io/pypi/v/bug-crowd-api-client.svg
[pypi]: https://pypi.python.org/pypi/bug-crowd-api-client
