# Lecture profile data

This package defines the topic-scoped knowledge profile extracted from one lecture.
The processing pipeline lives in `src/lecture_tutor/` and does not load the global
teacher profile.

Flow:

1. `src.common.stt` transcribes a local lecture video.
2. `src.common.media` samples board frames from a local video.
3. `lecture_tutor.analyze_lecture` analyzes transcript and frames into a draft
   `LECTURE_PROFILE_SCHEMA`.
4. `lecture_tutor.validate_lecture` checks relations mathematically and repairs likely
   extraction ambiguities; unresolved cases remain flagged rather than silently deleted.
5. `lecture_tutor.discover_problem` maps problem conditions to profile concepts; it does not reject questions.
6. `lecture_tutor.generate_solution` creates a lecture-grounded explanation.

The lecture profile records mathematical content and applicability conditions. It is
separate from the instructor-wide profile extracted from multiple worked-solution
videos. Student-work analysis is a later extension.
