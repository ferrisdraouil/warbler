"""User model tests."""

# run these tests like:
#
#    python -m unittest test_user_model.py

import os
from unittest import TestCase

from models import db, User, Message, FollowersFollowee

# BEFORE we import our app, let's set an environmental variable
# to use a different database for tests (we need to do this
# before we import our app, since that will have already
# connected to the database

os.environ['DATABASE_URL'] = "postgresql:///warbler-test"

# Now we can import app

from app import app

# Create our tables (we do this here, so we only create the tables
# once for all tests --- in each test, we'll delete the data
# and create fresh new clean test data

db.create_all()


class UserModelTestCase(TestCase):
    """Test views for messages."""

    def setUp(self):
        """Create test client, add sample data."""

        # u = User(
        #     email="test@test.com",
        #     username="testuser",
        #     password="HASHED_PASSWORD")
        # db.session.add(u)
        # db.session.commit()

        self.client = app.test_client()

    def tearDown(self):
        """Reset the conditions for testing"""
        Message.query.delete()
        FollowersFollowee.query.delete()
        User.query.delete()

    def test_user_model(self):
        """Does basic model work?"""

        # User should have no messages & no followers
        u = User(
            email="test@test.com",
            username="testuser",
            password="HASHED_PASSWORD")
        db.session.add(u)
        db.session.commit()

        self.assertEqual(len(u.messages), 0)
        self.assertEqual(len(u.followers), 0)

    def test_repr(self):
        """Does repr work"""

        u = User(
            email="test@test.com",
            username="testuser",
            password="HASHED_PASSWORD")
        db.session.add(u)
        db.session.commit()

        self.assertEqual(u.__repr__(),
                         f"<User #{u.id}: testuser, test@test.com>")

    def test_not_following_or_followed_by(self):
        """Test to make sure not following or followed by is functioning correctly"""

        u = User(
            email="test@test.com",
            username="testuser",
            password="HASHED_PASSWORD")
        db.session.add(u)
        db.session.commit()

        u2 = User(email="email@email.com", username="guy", password="guest")

        db.session.add(u2)
        db.session.commit()

        self.assertEqual(False, u.is_followed_by(u2))
        self.assertEqual(False, u.is_following(u2))

    def test_is_following_and_followed_by(self):
        """Test to make sure is following and followed by is functioning correctly"""

        u = User(
            email="test@test.com",
            username="testuser",
            password="HASHED_PASSWORD")
        db.session.add(u)
        db.session.commit()

        u2 = User(email="email@email.com", username="guy", password="guest")

        db.session.add(u2)
        db.session.commit()

        # user decides to follow
        # followee = User.query.get_or_404(u2.id)
        u.following.append(u2)
        db.session.commit()

        self.assertEqual(True, u2.is_followed_by(u))
        self.assertEqual(True, u.is_following(u2))

    def test_successful_user_creation(self):
        """Test that a properly entered user will be created"""

        u = User(
            email="test@test.com",
            username="testuser",
            password="HASHED_PASSWORD")
        db.session.add(u)
        db.session.commit()

        self.assertIsInstance(u, User)

    def test_failed_user_creation(self):
        """Test an improperly entered user will not be created"""

        u = User(email="bob@test.com", password="HASHED_PASSWORD")

        self.assertEqual(None, u.id)

    def test_user_authentication_successful(self):
        """Does User.authenticate successfully return a user when given a valid username and password?"""

        u = User(
            email="test@test.com",
            username="testuser",
            password="HASHED_PASSWORD")
        User.signup(
            email="test@test.com",
            username="testuser",
            password="HASHED_PASSWORD",
            image_url='http://www.a.com')
        db.session.commit()
        self.assertEqual(
            User.authenticate('testuser', 'HASHED_PASSWORD').username,
            u.username)

    def test_wrong_username_authentication(self):
        """Does User.authenticate fail to return a user when given an invalid username?"""

        u = User(
            email="test@test.com",
            username="testuser",
            password="HASHED_PASSWORD")
        User.signup(
            email="test@test.com",
            username="testuser",
            password="HASHED_PASSWORD",
            image_url='http://www.a.com')
        db.session.commit()
        self.assertEqual(User.authenticate('jimbo', 'HASHED_PASSWORD'), False)

    def test_wrong_password_authentication(self):
        """Does User.authenticate fail to return a user when given an invalid username?"""

        u = User(
            email="test@test.com",
            username="testuser",
            password="HASHED_PASSWORD")
        User.signup(
            email="test@test.com",
            username="testuser",
            password="HASHED_PASSWORD",
            image_url='http://www.a.com')
        db.session.commit()
        self.assertEqual(User.authenticate('testuser', '1234'), False)