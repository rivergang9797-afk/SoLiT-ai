# Teacher profile pipeline

This package analyzes problem-solving videos to derive reusable instructor policies
across problems. Its current analysis, discovery, validation, compression, and
generation stages remain independent from the lesson-scoped lecture profile.

Teacher-profile inputs and outputs are grouped under `data/teacher_profile/`.
Run commands from the repository root, for example:

```bash
python -m src.teacher_profile.discover
python -m src.teacher_profile.generate --policy-only \
  --policy data/teacher_profile/profiles/teacher_policy_v5.md
```
