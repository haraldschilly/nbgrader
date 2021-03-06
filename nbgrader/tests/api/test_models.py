import datetime
import pytest
import json

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, scoped_session
from sqlalchemy.sql import and_
from nbgrader import api


@pytest.fixture
def db(request):
    engine = create_engine("sqlite:///:memory:")
    db = scoped_session(sessionmaker(autoflush=True, bind=engine))
    api.Base.query = db.query_property()
    api.Base.metadata.create_all(bind=engine)

    def fin():
        db.close()
    request.addfinalizer(fin)

    return db


@pytest.fixture
def submissions(db):
    now = datetime.datetime.now()
    a = api.Assignment(name='foo', duedate=now)
    n = api.Notebook(name='blah', assignment=a)
    gc1 = api.GradeCell(
        name='foo', max_score=10, notebook=n, cell_type="markdown")
    gc2 = api.GradeCell(
        name='bar', max_score=5, notebook=n, cell_type="code")
    sc = api.SolutionCell(
        name='foo', notebook=n, cell_type='markdown')
    db.add(a)
    db.commit()

    s = api.Student(id="12345", first_name='Jane', last_name='Doe', email='janedoe@nowhere')
    sa = api.SubmittedAssignment(assignment=a, student=s)
    sn = api.SubmittedNotebook(assignment=sa, notebook=n)
    g1a = api.Grade(cell=gc1, notebook=sn)
    g2a = api.Grade(cell=gc2, notebook=sn)
    ca = api.Comment(cell=sc, notebook=sn)

    db.add(s)
    db.commit()

    s = api.Student(id="6789", first_name='John', last_name='Doe', email='johndoe@nowhere')
    sa = api.SubmittedAssignment(assignment=a, student=s)
    sn = api.SubmittedNotebook(assignment=sa, notebook=n)
    g1b = api.Grade(cell=gc1, notebook=sn)
    g2b = api.Grade(cell=gc2, notebook=sn)
    cb = api.Comment(cell=sc, notebook=sn)

    db.add(s)
    db.commit()

    return db, (g1a, g2a, g1b, g2b), (ca, cb)


def test_create_assignment(db):
    now = datetime.datetime.now()
    a = api.Assignment(name='foo', duedate=now)
    db.add(a)
    db.commit()

    assert a.id
    assert a.name == 'foo'
    assert a.duedate == now
    assert a.notebooks == []
    assert a.submissions == []

    assert a.max_score == 0
    assert a.max_code_score == 0
    assert a.max_written_score == 0
    assert a.num_submissions == 0

    assert repr(a) == "Assignment<foo>"


def test_create_notebook(db):
    now = datetime.datetime.now()
    a = api.Assignment(name='foo', duedate=now)
    n = api.Notebook(name='blah', assignment=a)
    db.add(a)
    db.commit()

    assert n.id
    assert n.name == 'blah'
    assert n.assignment == a
    assert n.grade_cells == []
    assert n.solution_cells == []
    assert n.submissions == []
    assert a.notebooks == [n]

    assert n.max_score == 0
    assert n.max_code_score == 0
    assert n.max_written_score == 0

    assert repr(n) == "Notebook<foo/blah>"


def test_create_grade_cell(db):
    now = datetime.datetime.now()
    a = api.Assignment(name='foo', duedate=now)
    n = api.Notebook(name='blah', assignment=a)
    g = api.GradeCell(
        name='foo', max_score=10, notebook=n, source="print('hello')",
        cell_type="code", checksum="12345")
    db.add(a)
    db.commit()

    assert g.id
    assert g.name == 'foo'
    assert g.max_score == 10
    assert g.source == "print('hello')"
    assert g.cell_type == "code"
    assert g.checksum == "12345"
    assert g.assignment == a
    assert g.notebook == n
    assert g.grades == []
    assert n.grade_cells == [g]

    assert n.max_score == 10
    assert n.max_code_score == 10
    assert n.max_written_score == 0

    assert repr(g) == "GradeCell<foo/blah/foo>"


def test_create_solution_cell(db):
    now = datetime.datetime.now()
    a = api.Assignment(name='foo', duedate=now)
    n = api.Notebook(name='blah', assignment=a)
    s = api.SolutionCell(
        name='foo', notebook=n, source="hello",
        cell_type="code", checksum="12345")
    db.add(a)
    db.commit()

    assert s.id
    assert s.name == 'foo'
    assert s.cell_type == "code"
    assert s.source == "hello"
    assert s.checksum == "12345"
    assert s.assignment == a
    assert s.notebook == n
    assert s.comments == []
    assert n.solution_cells == [s]

    assert repr(s) == "SolutionCell<foo/blah/foo>"


def test_create_student(db):
    s = api.Student(id="12345", first_name='Jane', last_name='Doe', email='janedoe@nowhere')
    db.add(s)
    db.commit()

    assert s.id == "12345"
    assert s.first_name == 'Jane'
    assert s.last_name == 'Doe'
    assert s.email == 'janedoe@nowhere'
    assert s.submissions == []

    assert s.score == 0
    assert s.max_score == 0

    assert repr(s) == "Student<12345>"


def test_create_submitted_assignment(db):
    a = api.Assignment(name='foo')
    s = api.Student(id="12345", first_name='Jane', last_name='Doe', email='janedoe@nowhere')
    sa = api.SubmittedAssignment(assignment=a, student=s)
    db.add(sa)
    db.commit()

    assert sa.id
    assert sa.assignment == a
    assert sa.student == s
    assert sa.notebooks == []
    assert s.submissions == [sa]
    assert a.submissions == [sa]

    assert sa.score == 0
    assert sa.max_score == 0
    assert sa.code_score == 0
    assert sa.max_code_score == 0
    assert sa.written_score == 0
    assert sa.max_written_score == 0
    assert not sa.needs_manual_grade

    assert sa.duedate == None
    assert sa.timestamp == None
    assert sa.extension == None
    assert sa.total_seconds_late == 0

    d = sa.to_dict()
    assert d['id'] == sa.id
    assert d['name'] == 'foo'
    assert d['student'] == '12345'
    assert d['duedate'] == None
    assert d['timestamp'] == None
    assert d['extension'] == None
    assert d['total_seconds_late'] == 0
    assert d['score'] == 0
    assert d['max_score'] == 0
    assert d['code_score'] == 0
    assert d['max_code_score'] == 0
    assert d['written_score'] == 0
    assert d['max_written_score'] == 0
    assert not d['needs_manual_grade']

    assert repr(sa) == "SubmittedAssignment<foo for 12345>"


def test_submission_timestamp_ontime(db):
    duedate = datetime.datetime.now()
    timestamp = duedate - datetime.timedelta(days=2)

    a = api.Assignment(name='foo', duedate=duedate)
    s = api.Student(id="12345", first_name='Jane', last_name='Doe', email='janedoe@nowhere')
    sa = api.SubmittedAssignment(assignment=a, student=s, timestamp=timestamp)
    db.add(sa)
    db.commit()

    assert sa.duedate == duedate
    assert sa.timestamp == timestamp
    assert sa.extension == None
    assert sa.total_seconds_late == 0

    d = sa.to_dict()
    assert d['duedate'] == duedate.isoformat()
    assert d['timestamp'] == timestamp.isoformat()
    assert d['extension'] == None
    assert d['total_seconds_late'] == 0


def test_submission_timestamp_late(db):
    duedate = datetime.datetime.now()
    timestamp = duedate + datetime.timedelta(days=2)

    a = api.Assignment(name='foo', duedate=duedate)
    s = api.Student(id="12345", first_name='Jane', last_name='Doe', email='janedoe@nowhere')
    sa = api.SubmittedAssignment(assignment=a, student=s, timestamp=timestamp)
    db.add(sa)
    db.commit()

    assert sa.duedate == duedate
    assert sa.timestamp == timestamp
    assert sa.extension == None
    assert sa.total_seconds_late == 172800

    d = sa.to_dict()
    assert d['duedate'] == duedate.isoformat()
    assert d['timestamp'] == timestamp.isoformat()
    assert d['extension'] == None
    assert d['total_seconds_late'] == 172800


def test_submission_timestamp_with_extension(db):
    duedate = datetime.datetime.now()
    timestamp = duedate + datetime.timedelta(days=2)
    extension = datetime.timedelta(days=3)

    a = api.Assignment(name='foo', duedate=duedate)
    s = api.Student(id="12345", first_name='Jane', last_name='Doe', email='janedoe@nowhere')
    sa = api.SubmittedAssignment(assignment=a, student=s, timestamp=timestamp, extension=extension)
    db.add(sa)
    db.commit()

    assert sa.duedate == (duedate + extension)
    assert sa.timestamp == timestamp
    assert sa.extension == extension
    assert sa.total_seconds_late == 0

    d = sa.to_dict()
    assert d['duedate'] == (duedate + extension).isoformat()
    assert d['timestamp'] == timestamp.isoformat()
    assert d['extension'] == extension.total_seconds()
    assert d['total_seconds_late'] == 0


def test_submission_timestamp_late_with_extension(db):
    duedate = datetime.datetime.now()
    timestamp = duedate + datetime.timedelta(days=5)
    extension = datetime.timedelta(days=3)

    a = api.Assignment(name='foo', duedate=duedate)
    s = api.Student(id="12345", first_name='Jane', last_name='Doe', email='janedoe@nowhere')
    sa = api.SubmittedAssignment(assignment=a, student=s, timestamp=timestamp, extension=extension)
    db.add(sa)
    db.commit()

    assert sa.duedate == (duedate + extension)
    assert sa.timestamp == timestamp
    assert sa.extension == extension
    assert sa.total_seconds_late == 172800

    d = sa.to_dict()
    assert d['duedate'] == (duedate + extension).isoformat()
    assert d['timestamp'] == timestamp.isoformat()
    assert d['extension'] == extension.total_seconds()
    assert d['total_seconds_late'] == 172800


def test_create_submitted_notebook(db):
    now = datetime.datetime.now()
    a = api.Assignment(name='foo', duedate=now)
    n = api.Notebook(name='blah', assignment=a)
    s = api.Student(id="12345", first_name='Jane', last_name='Doe', email='janedoe@nowhere')
    sa = api.SubmittedAssignment(assignment=a, student=s)
    sn = api.SubmittedNotebook(assignment=sa, notebook=n)
    db.add(sn)
    db.commit()

    assert sn.id
    assert sn.notebook == n
    assert sn.assignment == sa
    assert sn.grades == []
    assert sn.comments == []
    assert sn.student == s
    assert sa.notebooks == [sn]
    assert n.submissions == [sn]

    assert sn.score == 0
    assert sn.max_score == 0
    assert sn.code_score == 0
    assert sn.max_code_score == 0
    assert sn.written_score == 0
    assert sn.max_written_score == 0
    assert not sn.needs_manual_grade

    assert repr(sn) == "SubmittedNotebook<foo/blah for 12345>"


def test_create_code_grade(db):
    now = datetime.datetime.now()
    a = api.Assignment(name='foo', duedate=now)
    n = api.Notebook(name='blah', assignment=a)
    gc = api.GradeCell(
        name='foo', max_score=10, notebook=n, source="print('hello')",
        cell_type="code", checksum="12345")
    s = api.Student(id="12345", first_name='Jane', last_name='Doe', email='janedoe@nowhere')
    sa = api.SubmittedAssignment(assignment=a, student=s)
    sn = api.SubmittedNotebook(assignment=sa, notebook=n)
    g = api.Grade(cell=gc, notebook=sn, auto_score=5)
    db.add(g)
    db.commit()

    assert g.id
    assert g.cell == gc
    assert g.notebook == sn
    assert g.auto_score == 5
    assert g.manual_score == None
    assert g.assignment == sa
    assert g.student == s
    assert g.max_score == 10

    assert not g.needs_manual_grade
    assert not sn.needs_manual_grade
    assert not sa.needs_manual_grade

    assert g.score == 5
    assert sn.score == 5
    assert sn.code_score == 5
    assert sn.written_score == 0
    assert sa.score == 5
    assert sa.code_score == 5
    assert sa.written_score == 0
    assert s.score == 5

    g.manual_score = 7.5
    db.commit()

    assert not g.needs_manual_grade
    assert not sn.needs_manual_grade
    assert not sa.needs_manual_grade

    assert g.score == 7.5
    assert sn.score == 7.5
    assert sn.code_score == 7.5
    assert sn.written_score == 0
    assert sa.score == 7.5
    assert sa.code_score == 7.5
    assert sa.written_score == 0
    assert s.score == 7.5

    assert repr(g) == "Grade<foo/blah/foo for 12345>"


def test_create_written_grade(db):
    now = datetime.datetime.now()
    a = api.Assignment(name='foo', duedate=now)
    n = api.Notebook(name='blah', assignment=a)
    gc = api.GradeCell(
        name='foo', max_score=10, notebook=n, cell_type="markdown")
    s = api.Student(id="12345", first_name='Jane', last_name='Doe', email='janedoe@nowhere')
    sa = api.SubmittedAssignment(assignment=a, student=s)
    sn = api.SubmittedNotebook(assignment=sa, notebook=n)
    g = api.Grade(cell=gc, notebook=sn)
    db.add(g)
    db.commit()

    assert g.id
    assert g.cell == gc
    assert g.notebook == sn
    assert g.auto_score == None
    assert g.manual_score == None
    assert g.assignment == sa
    assert g.student == s
    assert g.max_score == 10

    assert g.needs_manual_grade
    assert sn.needs_manual_grade
    assert sa.needs_manual_grade

    assert g.score == 0
    assert sn.score == 0
    assert sn.code_score == 0
    assert sn.written_score == 0
    assert sa.score == 0
    assert sa.code_score == 0
    assert sa.written_score == 0
    assert s.score == 0

    g.manual_score = 7.5
    db.commit()

    assert not g.needs_manual_grade
    assert not sn.needs_manual_grade
    assert not sa.needs_manual_grade

    assert g.score == 7.5
    assert sn.score == 7.5
    assert sn.code_score == 0
    assert sn.written_score == 7.5
    assert sa.score == 7.5
    assert sa.code_score == 0
    assert sa.written_score == 7.5
    assert s.score == 7.5

    assert repr(g) == "Grade<foo/blah/foo for 12345>"


def test_create_comment(db):
    now = datetime.datetime.now()
    a = api.Assignment(name='foo', duedate=now)
    n = api.Notebook(name='blah', assignment=a)
    sc = api.SolutionCell(name='foo', notebook=n, cell_type="code")
    s = api.Student(id="12345", first_name='Jane', last_name='Doe', email='janedoe@nowhere')
    sa = api.SubmittedAssignment(assignment=a, student=s)
    sn = api.SubmittedNotebook(assignment=sa, notebook=n)
    c = api.Comment(cell=sc, notebook=sn, comment="something")
    db.add(c)
    db.commit()

    assert c.id
    assert c.cell == sc
    assert c.notebook == sn
    assert c.comment == "something"
    assert c.assignment == sa
    assert c.student == s

    assert repr(c) == "Comment<foo/blah/foo for 12345>"

def test_query_needs_manual_grade_ungraded(submissions):
    db = submissions[0]

    # do all the cells need grading?
    a = db.query(api.Grade)\
        .filter(api.Grade.needs_manual_grade)\
        .order_by(api.Grade.id)\
        .all()
    b = db.query(api.Grade)\
        .order_by(api.Grade.id)\
        .all()
    assert a == b

    # do all the submitted notebooks need grading?
    a = db.query(api.SubmittedNotebook)\
        .filter(api.SubmittedNotebook.needs_manual_grade)\
        .order_by(api.SubmittedNotebook.id)\
        .all()
    b = db.query(api.SubmittedNotebook)\
        .order_by(api.SubmittedNotebook.id)\
        .all()
    assert a == b

    # do all the notebooks need grading?
    a = db.query(api.Notebook)\
        .filter(api.Notebook.needs_manual_grade)\
        .order_by(api.Notebook.id)\
        .all()
    b = db.query(api.Notebook)\
        .order_by(api.Notebook.id)\
        .all()
    assert a == b

    # do all the assignments need grading?
    a = db.query(api.SubmittedAssignment)\
        .join(api.SubmittedNotebook, api.Grade)\
        .filter(api.SubmittedNotebook.needs_manual_grade)\
        .order_by(api.SubmittedAssignment.id)\
        .all()
    b = db.query(api.SubmittedAssignment)\
        .order_by(api.SubmittedAssignment.id)\
        .all()
    assert a == b

def test_query_needs_manual_grade_autograded(submissions):
    db, grades, _ = submissions

    for grade in grades:
        grade.auto_score = grade.max_score
    db.commit()

    # do none of the cells need grading?
    assert [] == db.query(api.Grade)\
        .filter(api.Grade.needs_manual_grade)\
        .all()

    # do none of the submitted notebooks need grading?
    assert [] == db.query(api.SubmittedNotebook)\
        .filter(api.SubmittedNotebook.needs_manual_grade)\
        .all()

    # do none of the notebooks need grading?
    assert [] == db.query(api.Notebook)\
        .filter(api.Notebook.needs_manual_grade)\
        .all()

    # do none of the assignments need grading?
    assert [] == db.query(api.SubmittedAssignment)\
        .join(api.SubmittedNotebook, api.Grade)\
        .filter(api.SubmittedNotebook.needs_manual_grade)\
        .all()

def test_query_needs_manual_grade_manualgraded(submissions):
    db, grades, _ = submissions

    for grade in grades:
        grade.auto_score = None
        grade.manual_score = grade.max_score / 2.0
    db.commit()

    # do none of the cells need grading?
    assert [] == db.query(api.Grade)\
        .filter(api.Grade.needs_manual_grade)\
        .all()

    # do none of the submitted notebooks need grading?
    assert [] == db.query(api.SubmittedNotebook)\
        .filter(api.SubmittedNotebook.needs_manual_grade)\
        .all()

    # do none of the notebooks need grading?
    assert [] == db.query(api.Notebook)\
        .filter(api.Notebook.needs_manual_grade)\
        .all()

    # do none of the assignments need grading?
    assert [] == db.query(api.SubmittedAssignment)\
        .join(api.SubmittedNotebook, api.Grade)\
        .filter(api.SubmittedNotebook.needs_manual_grade)\
        .all()

def test_query_max_score(submissions):
    db = submissions[0]

    assert [5, 10] == sorted([x[0] for x in db.query(api.GradeCell.max_score).all()])
    assert [5, 5, 10, 10] == sorted([x[1] for x in db.query(api.Grade.id, api.Grade.max_score).all()])
    assert [15] == sorted([x[1] for x in db.query(api.Notebook.id, api.Notebook.max_score).all()])
    assert [15, 15] == sorted([x[1] for x in db.query(api.SubmittedNotebook.id, api.SubmittedNotebook.max_score).all()])
    assert [15] == sorted([x[1] for x in db.query(api.Assignment.id, api.Assignment.max_score).all()])
    assert [15, 15] == sorted([x[1] for x in db.query(api.SubmittedAssignment.id, api.SubmittedAssignment.max_score).all()])
    assert [15, 15] == sorted([x[1] for x in db.query(api.Student.id, api.Student.max_score).all()])

def test_query_score_ungraded(submissions):
    db = submissions[0]

    assert [x[0] for x in db.query(api.Grade.score).all()] == [0.0, 0.0, 0.0, 0.0]
    assert [x[1] for x in db.query(api.SubmittedNotebook.id, api.SubmittedNotebook.score).all()] == [0.0, 0.0]
    assert [x[1] for x in db.query(api.SubmittedAssignment.id, api.SubmittedAssignment.score).all()] == [0.0, 0.0]
    assert [x[1] for x in db.query(api.Student.id, api.Student.score).all()] == [0.0, 0.0]

def test_query_score_autograded(submissions):
    db, grades, _ = submissions

    grades[0].auto_score = 10
    grades[1].auto_score = 0
    grades[2].auto_score = 5
    grades[3].auto_score = 2.5
    db.commit()

    assert sorted(x[0] for x in db.query(api.Grade.score).all()) == [0, 2.5, 5, 10]
    assert sorted(x[1] for x in db.query(api.SubmittedNotebook.id, api.SubmittedNotebook.score).all()) == [7.5, 10]
    assert sorted(x[1] for x in db.query(api.SubmittedAssignment.id, api.SubmittedAssignment.score).all()) == [7.5, 10]
    assert sorted(x[1] for x in db.query(api.Student.id, api.Student.score).all()) == [7.5, 10]

def test_query_score_manualgraded(submissions):
    db, grades, _ = submissions

    grades[0].auto_score = 10
    grades[1].auto_score = 0
    grades[2].auto_score = 5
    grades[3].auto_score = 2.5
    grades[0].manual_score = 4
    grades[1].manual_score = 1.5
    grades[2].manual_score = 9
    grades[3].manual_score = 3
    db.commit()

    assert sorted(x[0] for x in db.query(api.Grade.score).all()) == [1.5, 3, 4, 9]
    assert sorted(x[1] for x in db.query(api.SubmittedNotebook.id, api.SubmittedNotebook.score).all()) == [5.5, 12]
    assert sorted(x[1] for x in db.query(api.SubmittedAssignment.id, api.SubmittedAssignment.score).all()) == [5.5, 12]
    assert sorted(x[1] for x in db.query(api.Student.id, api.Student.score).all()) == [5.5, 12]

def test_query_max_written_score(submissions):
    db = submissions[0]

    assert [10] == sorted([x[1] for x in db.query(api.Notebook.id, api.Notebook.max_written_score).all()])
    assert [10, 10] == sorted([x[1] for x in db.query(api.SubmittedNotebook.id, api.SubmittedNotebook.max_written_score).all()])
    assert [10] == sorted([x[1] for x in db.query(api.Assignment.id, api.Assignment.max_written_score).all()])
    assert [10, 10] == sorted([x[1] for x in db.query(api.SubmittedAssignment.id, api.SubmittedAssignment.max_written_score).all()])

def test_query_written_score_ungraded(submissions):
    db = submissions[0]

    assert [0.0, 0.0] == [x[1] for x in db.query(api.SubmittedNotebook.id, api.SubmittedNotebook.written_score).all()]
    assert [0.0, 0.0] == [x[1] for x in db.query(api.SubmittedAssignment.id, api.SubmittedAssignment.written_score).all()]

def test_query_written_score_autograded(submissions):
    db, grades, _ = submissions

    grades[0].auto_score = 10
    grades[1].auto_score = 0
    grades[2].auto_score = 5
    grades[3].auto_score = 2.5
    db.commit()

    assert [5, 10] == sorted(x[1] for x in db.query(api.SubmittedNotebook.id, api.SubmittedNotebook.written_score).all())
    assert [5, 10] == sorted(x[1] for x in db.query(api.SubmittedAssignment.id, api.SubmittedAssignment.written_score).all())

def test_query_written_score_manualgraded(submissions):
    db, grades, _ = submissions

    grades[0].auto_score = 10
    grades[1].auto_score = 0
    grades[2].auto_score = 5
    grades[3].auto_score = 2.5
    grades[0].manual_score = 4
    grades[1].manual_score = 1.5
    grades[2].manual_score = 9
    grades[3].manual_score = 3
    db.commit()

    assert [4, 9] == sorted(x[1] for x in db.query(api.SubmittedNotebook.id, api.SubmittedNotebook.written_score).all())
    assert [4, 9] == sorted(x[1] for x in db.query(api.SubmittedAssignment.id, api.SubmittedAssignment.written_score).all())

def test_query_max_code_score(submissions):
    db = submissions[0]

    assert [5] == sorted([x[1] for x in db.query(api.Notebook.id, api.Notebook.max_code_score).all()])
    assert [5, 5] == sorted([x[1] for x in db.query(api.SubmittedNotebook.id, api.SubmittedNotebook.max_code_score).all()])
    assert [5] == sorted([x[1] for x in db.query(api.Assignment.id, api.Assignment.max_code_score).all()])
    assert [5, 5] == sorted([x[1] for x in db.query(api.SubmittedAssignment.id, api.SubmittedAssignment.max_code_score).all()])

def test_query_code_score_ungraded(submissions):
    db = submissions[0]

    assert [0.0, 0.0] == [x[1] for x in db.query(api.SubmittedNotebook.id, api.SubmittedNotebook.code_score).all()]
    assert [0.0, 0.0] == [x[1] for x in db.query(api.SubmittedAssignment.id, api.SubmittedAssignment.code_score).all()]

def test_query_code_score_autograded(submissions):
    db, grades, _ = submissions

    grades[0].auto_score = 10
    grades[1].auto_score = 0
    grades[2].auto_score = 5
    grades[3].auto_score = 2.5
    db.commit()

    assert [0, 2.5] == sorted(x[1] for x in db.query(api.SubmittedNotebook.id, api.SubmittedNotebook.code_score).all())
    assert [0, 2.5] == sorted(x[1] for x in db.query(api.SubmittedAssignment.id, api.SubmittedAssignment.code_score).all())

def test_query_code_score_manualgraded(submissions):
    db, grades, _ = submissions

    grades[0].auto_score = 10
    grades[1].auto_score = 0
    grades[2].auto_score = 5
    grades[3].auto_score = 2.5
    grades[0].manual_score = 4
    grades[1].manual_score = 1.5
    grades[2].manual_score = 9
    grades[3].manual_score = 3
    db.commit()

    assert [1.5, 3] == sorted(x[1] for x in db.query(api.SubmittedNotebook.id, api.SubmittedNotebook.code_score).all())
    assert [1.5, 3] == sorted(x[1] for x in db.query(api.SubmittedAssignment.id, api.SubmittedAssignment.code_score).all())

def test_query_num_submissions(submissions):
    db = submissions[0]

    assert [2] == [x[0] for x in db.query(api.Assignment.num_submissions).all()]
    assert [2] == [x[0] for x in db.query(api.Notebook.num_submissions).all()]

def test_student_max_score(db):
    now = datetime.datetime.now()
    a = api.Assignment(name='foo', duedate=now)
    n = api.Notebook(name='blah', assignment=a)
    api.GradeCell(
        name='foo', max_score=10, notebook=n, cell_type="markdown")
    api.GradeCell(
        name='bar', max_score=5, notebook=n, cell_type="code")
    db.add(a)
    db.commit()

    s = api.Student(id="12345", first_name='Jane', last_name='Doe', email='janedoe@nowhere')
    db.add(s)
    db.commit()

    assert s.max_score == 15

def test_query_grade_cell_types(submissions):
    db = submissions[0]

    a = db.query(api.Grade)\
        .filter(api.Grade.cell_type == "code")\
        .order_by(api.Grade.id)\
        .all()
    b = db.query(api.Grade)\
        .join(api.GradeCell)\
        .filter(api.GradeCell.cell_type == "code")\
        .order_by(api.Grade.id)\
        .all()
    assert a == b

    a = db.query(api.Grade)\
        .filter(api.Grade.cell_type == "markdown")\
        .order_by(api.Grade.id)\
        .all()
    b = db.query(api.Grade)\
        .join(api.GradeCell)\
        .filter(api.GradeCell.cell_type == "markdown")\
        .order_by(api.Grade.id)\
        .all()
    assert a == b

def test_query_failed_tests_failed(submissions):
    db, grades, _ = submissions

    for grade in grades:
        if grade.cell.cell_type == "code":
            grade.auto_score = 0
    db.commit()

    # have all the cells failed?
    a = db.query(api.Grade)\
        .filter(api.Grade.failed_tests)\
        .order_by(api.Grade.id)\
        .all()
    b = db.query(api.Grade)\
        .filter(api.Grade.cell_type == "code")\
        .order_by(api.Grade.id)\
        .all()
    assert a == b

    # have all the notebooks failed?
    a = db.query(api.SubmittedNotebook)\
        .filter(api.SubmittedNotebook.failed_tests)\
        .order_by(api.SubmittedNotebook.id)\
        .all()
    b = db.query(api.SubmittedNotebook)\
        .order_by(api.SubmittedNotebook.id)\
        .all()

def test_query_failed_tests_ok(submissions):
    db, all_grades, _ = submissions

    for grade in all_grades:
        if grade.cell.cell_type == "code":
            grade.auto_score = grade.max_score
    db.commit()

    # are all the grades ok?
    assert [] == db.query(api.Grade)\
        .filter(api.Grade.failed_tests)\
        .all()

    # are all the notebooks ok?
    assert [] == db.query(api.SubmittedNotebook)\
        .filter(api.SubmittedNotebook.failed_tests)\
        .all()


def test_assignment_to_dict(submissions):
    db = submissions[0]

    a = db.query(api.Assignment).one()
    ad = a.to_dict()

    assert set(ad.keys()) == {
        'id', 'name', 'duedate', 'num_submissions', 'max_score',
        'max_code_score', 'max_written_score'}

    assert ad['id'] == a.id
    assert ad['name'] == "foo"
    assert ad['duedate'] == a.duedate.isoformat()
    assert ad['num_submissions'] == 2
    assert ad['max_score'] == 15
    assert ad['max_code_score'] == 5
    assert ad['max_written_score'] == 10

    # make sure it can be JSONified
    json.dumps(ad)


def test_notebook_to_dict(submissions):
    db = submissions[0]

    a = db.query(api.Assignment).one()
    n, = a.notebooks
    nd = n.to_dict()

    assert set(nd.keys()) == {
        'id', 'name', 'num_submissions', 'max_score', 'max_code_score',
        'max_written_score', 'needs_manual_grade'}

    assert nd['id'] == n.id
    assert nd['name'] == 'blah'
    assert nd['num_submissions'] == 2
    assert nd['max_score'] == 15
    assert nd['max_code_score'] == 5
    assert nd['max_written_score'] == 10
    assert nd['needs_manual_grade']

    # make sure it can be JSONified
    json.dumps(nd)


def test_gradecell_to_dict(submissions):
    db = submissions[0]

    gc1 = db.query(api.GradeCell).filter(api.GradeCell.name == 'foo').one()
    gc2 = db.query(api.GradeCell).filter(api.GradeCell.name == 'bar').one()

    gc1d = gc1.to_dict()
    gc2d = gc2.to_dict()

    assert set(gc1d.keys()) == set(gc2d.keys())
    assert set(gc1d.keys()) == {
        'id', 'name', 'max_score', 'cell_type', 'source',
        'checksum', 'notebook', 'assignment'}

    assert gc1d['id'] == gc1.id
    assert gc1d['name'] == 'foo'
    assert gc1d['max_score'] == 10
    assert gc1d['cell_type'] == 'markdown'
    assert gc1d['source'] is None
    assert gc1d['checksum'] is None
    assert gc1d['notebook'] == 'blah'
    assert gc1d['assignment'] == 'foo'

    assert gc2d['id'] == gc2.id
    assert gc2d['name'] == 'bar'
    assert gc2d['max_score'] == 5
    assert gc2d['cell_type'] == 'code'
    assert gc2d['source'] is None
    assert gc2d['checksum'] is None
    assert gc2d['notebook'] == 'blah'
    assert gc2d['assignment'] == 'foo'

    # make sure it can be JSONified
    json.dumps(gc1d)
    json.dumps(gc2d)


def test_solutioncell_to_dict(submissions):
    db = submissions[0]

    sc = db.query(api.SolutionCell).one()
    scd = sc.to_dict()

    assert set(scd.keys()) == {
        'id', 'name', 'cell_type', 'source', 'checksum',
        'notebook', 'assignment'}

    assert scd['id'] == sc.id
    assert scd['name'] == 'foo'
    assert scd['cell_type'] == 'markdown'
    assert scd['source'] is None
    assert scd['checksum'] is None
    assert scd['notebook'] == 'blah'
    assert scd['assignment'] == 'foo'

    # make sure it can be JSONified
    json.dumps(scd)


def test_student_to_dict(submissions):
    db = submissions[0]

    s1 = db.query(api.Student).filter(api.Student.id == '12345').one()
    s2 = db.query(api.Student).filter(api.Student.id == '6789').one()

    s1d = s1.to_dict()
    s2d = s2.to_dict()

    assert set(s1d.keys()) == set(s2d.keys())
    assert set(s1d.keys()) == {
        'id', 'first_name', 'last_name', 'email', 'score', 'max_score'}

    assert s1d['id'] == '12345'
    assert s1d['first_name'] == 'Jane'
    assert s1d['last_name'] == 'Doe'
    assert s1d['email'] == 'janedoe@nowhere'
    assert s1d['score'] == 0
    assert s1d['max_score'] == 15

    assert s2d['id'] == '6789'
    assert s2d['first_name'] == 'John'
    assert s2d['last_name'] == 'Doe'
    assert s2d['email'] == 'johndoe@nowhere'
    assert s2d['score'] == 0
    assert s2d['max_score'] == 15

    # make sure it can be JSONified
    json.dumps(s1d)
    json.dumps(s2d)


def test_submittedassignment_to_dict(submissions):
    db = submissions[0]

    sa = db.query(api.SubmittedAssignment)\
        .join(api.Student)\
        .filter(api.Student.id == '12345')\
        .one()

    sad = sa.to_dict()

    assert set(sad.keys()) == {
        'id', 'name', 'student', 'timestamp', 'extension', 'duedate',
        'total_seconds_late', 'score', 'max_score', 'code_score',
        'max_code_score', 'written_score', 'max_written_score',
        'needs_manual_grade'}

    assert sad['id'] == sa.id
    assert sad['name'] == 'foo'
    assert sad['student'] == '12345'
    assert sad['timestamp'] is None
    assert sad['extension'] is None
    assert sad['duedate'] == sa.assignment.duedate.isoformat()
    assert sad['total_seconds_late'] == 0
    assert sad['score'] == 0
    assert sad['max_score'] == 15
    assert sad['code_score'] == 0
    assert sad['max_code_score'] == 5
    assert sad['written_score'] == 0
    assert sad['max_written_score'] == 10
    assert sad['needs_manual_grade']

    # make sure it can be JSONified
    json.dumps(sad)


def test_submittednotebook_to_dict(submissions):
    db = submissions[0]

    sn = db.query(api.SubmittedNotebook)\
        .join(api.Notebook, api.SubmittedAssignment, api.Student)\
        .filter(and_(
            api.Student.id == '12345',
            api.Notebook.name == 'blah'))\
        .one()

    snd = sn.to_dict()

    assert set(snd.keys()) == {
        'id', 'name', 'student', 'score', 'max_score', 'code_score',
        'max_code_score', 'written_score', 'max_written_score',
        'needs_manual_grade', 'failed_tests'}

    assert snd['id'] == sn.id
    assert snd['name'] == 'blah'
    assert snd['student'] == '12345'
    assert snd['score'] == 0
    assert snd['max_score'] == 15
    assert snd['code_score'] == 0
    assert snd['max_code_score'] == 5
    assert snd['written_score'] == 0
    assert snd['max_written_score'] == 10
    assert snd['needs_manual_grade']
    assert not snd['failed_tests']

    # make sure it can be JSONified
    json.dumps(snd)


def test_grade_to_dict(submissions):
    _, grades, _ = submissions

    for g in grades:
        gd = g.to_dict()
        assert set(gd.keys()) == {
            'id', 'name', 'notebook', 'assignment', 'student', 'auto_score',
            'manual_score', 'max_score', 'needs_manual_grade', 'failed_tests',
            'cell_type'}

        assert gd['id'] == g.id
        assert gd['name'] == g.name
        assert gd['notebook'] == 'blah'
        assert gd['assignment'] == 'foo'
        assert gd['student'] == g.student.id
        assert gd['auto_score'] is None
        assert gd['manual_score'] is None
        assert gd['needs_manual_grade']
        assert not gd['failed_tests']
        assert gd['cell_type'] == g.cell_type

        # make sure it can be JSONified
        json.dumps(gd)


def test_comment_to_dict(submissions):
    _, _, comments = submissions

    for c in comments:
        cd = c.to_dict()
        assert set(cd.keys()) == {
            'id', 'name', 'notebook', 'assignment', 'student', 'comment'}

        assert cd['id'] == c.id
        assert cd['name'] == c.name
        assert cd['notebook'] == 'blah'
        assert cd['assignment'] == 'foo'
        assert cd['student'] == c.student.id
        assert cd['comment'] is None

        # make sure it can be JSONified
        json.dumps(cd)
