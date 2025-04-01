# LurchCal Documentation

## Introduction

## Adding information to tasks

Task in ZIM already have meta information:

- start or due date, e.e. <2024-12-23 means due before Christmas.
- priority, designated with '!'. Multiple questionmarks denote higher priority [^1].
- Tasks can contain tags, starting with '@'.
  
This tool adds the following additional meta data:
- '\~' duration '\~' ['a']

This specifies the duration of a task, whereas duration can be written in hours, minutes, etc. If no duration is specfied, a configurable value is assigned (e.g., 6 min).

If the duration is specified at the top level task of subtasks, the duration is distributed evenly among the subtasks.
If 'a', which is optional, is specified, each subtasks gets assigned the specified duration of the parent task.

### Examples

> - [ ] task which lasts 10 minutes \~10m\~
> - [ ] task with each subtasks lasting 5 minutes \~10m\~
>   - [ ] task lasts 5 min (automatically computed)
>   - [ ] task also lasts 5 min (automatically computed)
> - [ ] task with each subtasks lasting 15 minutes \~15m\~a
>   - [ ] task lasts 15 min (assigned from parent)
>   - [ ] task also lasts 15 min (assigned from parent)

# End Notes

[^1]: Although Terry Pratchett argued that "Multiple exclamation marks are a sure sign of a diseased mind." Maybe he was a project manager?
