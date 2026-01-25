"""Type definitions for (a subset of) the JSON Resume schema.

The JSON Resume schema is broad; this project types only the fields we render.
Unknown fields are still preserved at runtime because input data is plain JSON.
"""

from __future__ import annotations

from typing import TypedDict


class Profile(TypedDict, total=False):
    network: str
    username: str
    url: str


class Location(TypedDict, total=False):
    city: str
    region: str
    countryCode: str


class Basics(TypedDict, total=False):
    name: str
    label: str
    email: str
    phone: str
    summary: str
    url: str
    location: Location
    profiles: list[Profile]


class WorkItem(TypedDict, total=False):
    company: str
    position: str
    location: str
    url: str
    startDate: str
    endDate: str
    summary: str
    highlights: list[str]


class WorkItemView(WorkItem, total=False):
    dateRange: str


class ProjectItem(TypedDict, total=False):
    name: str
    description: str
    url: str
    startDate: str
    endDate: str
    highlights: list[str]


class ProjectItemView(ProjectItem, total=False):
    dateRange: str


class SkillItem(TypedDict, total=False):
    name: str
    keywords: list[str]


class EducationItem(TypedDict, total=False):
    institution: str
    studyType: str
    area: str
    startDate: str
    endDate: str
    score: str


class PublicationItem(TypedDict, total=False):
    name: str
    publisher: str
    releaseDate: str
    url: str
    summary: str


class VolunteerItem(TypedDict, total=False):
    organization: str
    position: str
    url: str
    startDate: str
    endDate: str
    summary: str
    highlights: list[str]


class LanguageItem(TypedDict, total=False):
    language: str
    fluency: str


class Resume(TypedDict, total=False):
    basics: Basics
    work: list[WorkItem]
    education: list[EducationItem]
    skills: list[SkillItem]
    projects: list[ProjectItem]
    publications: list[PublicationItem]
    volunteer: list[VolunteerItem]
    languages: list[LanguageItem]


class ResumeView(TypedDict, total=False):
    basics: Basics
    work: list[WorkItemView]
    education: list[EducationItem]
    skills: list[SkillItem]
    projects: list[ProjectItemView]
    publications: list[PublicationItem]
    volunteer: list[VolunteerItem]
    languages: list[LanguageItem]
