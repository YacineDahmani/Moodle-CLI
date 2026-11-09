import json
from typing import Any, Dict, List, Optional
from moodle_cli.core.config import Config
from moodle_cli.core.api import MoodleClient, MoodleError
from moodle_cli.ui.console import console, display_courses_table, display_course_tree


def get_courses(config: Config) -> List[Dict[str, Any]]:
    client = MoodleClient(config)
    with console.status("[bold cyan]Fetching enrolled courses...[/bold cyan]"):
        return client.get_courses()


def list_courses(config: Config, json_output: bool = False) -> None:
    try:
        courses = get_courses(config)
        if json_output:
            console.print(json.dumps(courses, indent=2))
        else:
            display_courses_table(courses)
    except MoodleError as e:
        console.print(f"[red]Error fetching courses: {e}[/red]")


def view_course_contents(config: Config, course_id: int) -> None:
    client = MoodleClient(config)
    try:
        with console.status(f"[bold cyan]Fetching contents for course {course_id}...[/bold cyan]"):
            contents = client.get_course_contents(course_id)
            courses = client.get_courses()
            matched = next((c for c in courses if c.get("id") == course_id), None)
            course_name = matched.get("fullname", f"Course {course_id}") if matched else f"Course {course_id}"

        display_course_tree(course_name, contents)
    except MoodleError as e:
        console.print(f"[red]Error fetching course contents: {e}[/red]")
