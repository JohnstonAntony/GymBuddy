import json
import os
import click
from flask.cli import with_appcontext
from app.extensions import db
from app.models import Exercise


@click.command("seed-exercises")
@with_appcontext
def seed_exercises():
    """loads exercise data from a JSON file and inserts it into the database. Skips exercises that already exist to avoid duplicates"""
    seed_path = os.path.join(
        os.path.dirname(__file__), "seed_data", "exercises.json"
    )

    with open(seed_path, "r") as f:
        exercises_data = json.load(f)

    inserted = 0
    skipped = 0

    for entry in exercises_data:
        #skips if an exercise with this name already exists
        existing = Exercise.query.filter_by(name=entry["name"]).first()
        if existing:
            skipped += 1
            continue

        exercise = Exercise(
            name=entry["name"],
            category=entry["category"],
            muscle_groups=entry["muscle_groups"],
            equipment_required=entry.get("equipment_required"),
            description=entry.get("description"),
        )
        db.session.add(exercise)
        inserted += 1

    db.session.commit()
    click.echo(f"Seeded exercises: {inserted} inserted, {skipped} skipped (already present).")


def register_commands(app):
    """attach CLI commands to the Flask app. Called during app creation."""
    app.cli.add_command(seed_exercises)