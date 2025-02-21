from CTFd import utils
from CTFd.models import Challenges, Flags, Solves, Teams, Users, db
from CTFd.plugins import register_plugin_assets_directory
from CTFd.utils.decorators import admins_only
from CTFd.utils.email import sendmail
from CTFd.utils.logging import log
from CTFd.utils.user import get_current_team, get_current_user
from flask import Blueprint, redirect, render_template, request, url_for


# Define a new database model for tracking wrong flag submissions
class WrongFlagSubmissions(db.Model):
    __tablename__ = "wrong_flag_submissions"
    id = db.Column(db.Integer, primary_key=True)
    team_id = db.Column(
        db.Integer, db.ForeignKey("teams.id", ondelete="CASCADE"), nullable=False
    )
    challenge_id = db.Column(
        db.Integer, db.ForeignKey("challenges.id", ondelete="CASCADE"), nullable=False
    )
    count = db.Column(
        db.Integer, default=1, nullable=False
    )  # Number of times this happened

    def __init__(self, team_id, challenge_id):
        self.team_id = team_id
        self.challenge_id = challenge_id
        self.count = 1


def load(app):
    plugin_blueprint = Blueprint(
        "wrong_flag_detector",
        __name__,
        template_folder="templates",
    )

    # Ensure our table is created
    with app.app_context():
        db.create_all()

    # Admin panel route
    @plugin_blueprint.route("/admin/wrong_flags")
    @admins_only
    def view_wrong_flags():
        wrong_submissions = WrongFlagSubmissions.query.all()
        return render_template("wrong_flags.html", wrong_submissions=wrong_submissions)

    # Route to delete an entry
    @plugin_blueprint.route("/admin/wrong_flags/delete/<int:entry_id>")
    @admins_only
    def delete_wrong_flag(entry_id):
        entry = WrongFlagSubmissions.query.get(entry_id)
        if entry:
            db.session.delete(entry)
            db.session.commit()
        return redirect(url_for("wrong_flag_detector.view_wrong_flags"))

    app.register_blueprint(plugin_blueprint)


def monitor_wrong_flags():
    data = request.get_json()
    challenge_id = data.get("challenge_id")
    submission = data.get("submission")
    user = get_current_user()

    if not user:
        return None

    team = get_current_team()  # Get the user's team
    team_id = team.id if team else user.id  # Track individually if no team

    # Get all flags from the database
    all_flags = Flags.query.all()

    return next(
        (
            check_for_wrong_flags(team_id, challenge_id, flag, submission)
            for flag in all_flags
            if flag.content == submission and flag.challenge_id != challenge_id
        ),
        None,
    )


def check_for_wrong_flags(team_id, challenge_id, flag, submission):
    # Check if this team already has a wrong submission recorded
    existing_entry = WrongFlagSubmissions.query.filter_by(
        team_id=team_id, challenge_id=challenge_id
    ).first()

    if existing_entry:
        existing_entry.count += 1
    else:
        new_entry = WrongFlagSubmissions(team_id, challenge_id)
        db.session.add(new_entry)

    db.session.commit()

    log(
        "submission",
        f"Team {team_id} submitted a valid flag for Challenge {flag.challenge_id} to Challenge {challenge_id}. Attempt #{existing_entry.count if existing_entry else 1}",
    )

    # Notify admins if more than 2 wrong submissions happen
    if (existing_entry and existing_entry.count > 2) or (
        not existing_entry and new_entry.count > 2
    ):
        notify_admins(team_id, challenge_id, submission)

    return None  # Do not alert the user


def notify_admins(team_id, challenge_id, flag):
    """Send an email or log notification to administrators."""
    admin_emails = get_admin_emails()
    subject = f"Suspicious Flag Submissions from Team {team_id}"
    body = (
        f"Team {team_id} has submitted a valid flag (`{flag}`) to the wrong challenge ({challenge_id}) more than twice.\n\n"
        "This could indicate accidental confusion or an attempt to guess flag locations."
    )

    log("security", body)

    # Send email to admins
    for email in admin_emails:
        sendmail(email, subject, body)


def get_admin_emails():
    """Retrieve a list of admin emails."""
    admin_users = Users.query.filter_by(type="admin").all()
    return [admin.email for admin in admin_users if admin.email]
