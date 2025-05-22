# - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
# Copyright (C) 2023-2025 theoky
# - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
"""
"""
from durations_nlp import Duration

from datetime import datetime, time, date, timedelta
import re

tag_re = r"\@(\w+)"


class Task(object):
    def __init__(
        self,
        descr,
        prio=0,
        start_date=None,
        due_date=None,
        source_name="",
        has_children=False,
        id=0,
        parent=0,
        duration=6,
    ):
        self.prio = prio
        self.description = descr
        self.duration = duration
        self.is_default_duration = True
        self.assign_duration = False
        self.distribute_duration = True  # default

        self.create_appt_anyway = False
        self.block_time = False
        
        self.source_name = source_name
        self.has_children = has_children
        self.tags = []
        self.id = id
        self.subid = 0
        self.parent = parent
        try:
            d = date.fromisoformat(due_date)
        except:
            d = None
        self.due_date = d

        try:
            d = date.fromisoformat(start_date)
        except:
            d = None
        self.start_date = d

        # Dependency attributes
        self.depends_on_ids = []
        self.is_ready_to_schedule = True # Will be set to False if depends_on_ids is populated
        self.scheduled_start_time = None
        self.scheduled_end_time = None

        # Recurrence attributes
        self.is_recurring = False
        self.recurrence_rule = None
        self.recurrence_interval = None
        self.recurrence_on = None  # For weekly/monthly specifics like "MON" or "15" or "last TUE"
        self.recurrence_end_date = None
        self.recurrence_count = None
        self.original_start_date = self.start_date # Anchor for recurrence

        self.parse(descr)
        pass

    def parse(self, descr):
        d = descr.split("~")
        if len(d) >= 3:
            try:
                self.duration = Duration(d[1]).to_minutes()
                self.is_default_duration = False

                self.assign_duration = False
                self.distribute_duration = True

                if d[2]:
                    first_letter = d[2][0]
                    if first_letter == "a":
                        self.assign_duration = True
                        self.distribute_duration = False

            #                if first_letter == '~d' or d[2] =='~':

            except:
                pass
                # self.duration = 6.0

        m = re.findall(tag_re, descr, re.U)

        for t in m:
            self.tags.append(t.lower())

        # Parse recurrence rules
        # General pattern to find and extract the whole recurrence string first
        recurrence_match = re.search(r"repeats:\s*(.+)", descr, re.IGNORECASE)
        if recurrence_match:
            original_full_description_string = descr # Keep the original description

            recurrence_candidate_str = recurrence_match.group(1).strip() # The part after "repeats: "
            self.is_recurring = True
            
            # Determine prefix (part before "repeats:")
            prefix_descr = original_full_description_string[:recurrence_match.start()]
            
            # temp_recurrence_processing_str will be whittled down to get the suffix
            temp_recurrence_processing_str = recurrence_candidate_str

            # Define patterns for different recurrence types
            # Daily: repeats: daily [every N days] [until YYYY-MM-DD | count N]
            daily_pattern = re.compile(r"daily(?:\s+every\s+(\d+)\s+days?)?", re.IGNORECASE)
            # Weekly: repeats: weekly [every N weeks] [on weekday] [until YYYY-MM-DD | count N]
            weekly_pattern = re.compile(r"weekly(?:\s+every\s+(\d+)\s+weeks?)?(?:\s+on\s+(MON|TUE|WED|THU|FRI|SAT|SUN))?", re.IGNORECASE)
            # Monthly: repeats: monthly [every N months] [on day_number|last_weekday|first_weekday] [until YYYY-MM-DD | count N]
            monthly_pattern = re.compile(r"monthly(?:\s+every\s+(\d+)\s+months?)?(?:\s+on\s+((\d{1,2})|(last\s+(?:MON|TUE|WED|THU|FRI|SAT|SUN))|(first\s+(?:MON|TUE|WED|THU|FRI|SAT|SUN))))?", re.IGNORECASE)

            # End condition: until YYYY-MM-DD | count N
            end_condition_pattern = re.compile(r"(?:until\s+(\d{4}-\d{2}-\d{2})|count\s+(\d+))", re.IGNORECASE)

            # Check for daily recurrence
            match = daily_pattern.match(temp_recurrence_processing_str)
            if match:
                self.recurrence_rule = "daily"
                self.recurrence_interval = int(match.group(1)) if match.group(1) else 1
                temp_recurrence_processing_str = daily_pattern.sub("", temp_recurrence_processing_str, 1).strip()

            # Check for weekly recurrence
            if not self.recurrence_rule: # only if not already matched by daily
                match = weekly_pattern.match(temp_recurrence_processing_str)
                if match:
                    self.recurrence_rule = "weekly"
                    self.recurrence_interval = int(match.group(1)) if match.group(1) else 1
                    self.recurrence_on = match.group(2).upper() if match.group(2) else None
                    temp_recurrence_processing_str = weekly_pattern.sub("", temp_recurrence_processing_str, 1).strip()

            # Check for monthly recurrence
            if not self.recurrence_rule: # only if not already matched by daily or weekly
                match = monthly_pattern.match(temp_recurrence_processing_str)
                if match:
                    self.recurrence_rule = "monthly"
                    self.recurrence_interval = int(match.group(1)) if match.group(1) else 1
                    self.recurrence_on = match.group(2) if match.group(2) else None # This can be day number, "last MON", "first TUE"
                    temp_recurrence_processing_str = monthly_pattern.sub("", temp_recurrence_processing_str, 1).strip()
            
            # Parse end condition
            end_match = end_condition_pattern.search(temp_recurrence_processing_str) # search in what's left
            if end_match:
                if end_match.group(1): # until YYYY-MM-DD
                    try:
                        self.recurrence_end_date = date.fromisoformat(end_match.group(1))
                        temp_recurrence_processing_str = temp_recurrence_processing_str.replace(end_match.group(0), "", 1).strip()
                    except ValueError:
                        pass 
                elif end_match.group(2): # count N
                    self.recurrence_count = int(end_match.group(2))
                    temp_recurrence_processing_str = temp_recurrence_processing_str.replace(end_match.group(0), "", 1).strip()

            # After parsing, temp_recurrence_processing_str contains the part of the blob after "repeats:" that was NOT a rule.
            # This is the suffix.
            suffix_descr = temp_recurrence_processing_str.strip()
            
            current_description = ""
            if not suffix_descr: # Suffix is empty
                current_description = prefix_descr.strip()
            else:
                if not prefix_descr.strip(): # Prefix is empty
                    current_description = suffix_descr
                else: # Both prefix and suffix have content
                    current_description = (prefix_descr.strip() + " " + suffix_descr).strip()
            
            self.description = current_description
        
            # Re-parse tags from the new self.description
            self.tags = [] 
            m_tags_updated = re.findall(tag_re, self.description, re.U)
            for t_u in m_tags_updated:
                self.tags.append(t_u.lower())
        # If no recurrence_match, self.description remains as it was (processed by duration/tag parsing earlier if applicable)

        # Parse dependencies
        # depends_on: ID1,ID2,...
        # Regex explanation:
        # r"depends_on:\s*" : Matches "depends_on:" followed by zero or more whitespace.
        # r"((?:[\d]+)(?:\s*,\s*[\d]+)*)" : This is group(1). It captures:
        #      (?:[\d]+) : A non-capturing group for one or more digits (an ID).
        #      (?:\s*,\s*[\d]+)* : A non-capturing group that matches (zero or more times):
        #                           \s*,\s* : A comma, potentially surrounded by whitespace.
        #                           [\d]+   : Followed by another ID.
        # This ensures we capture a full list like "1, 2, 33" correctly as group(1).
        dependency_pattern = r"depends_on:\s*((?:[\d]+)(?:\s*,\s*[\d]+)*)"
        dependency_match = re.search(dependency_pattern, self.description, re.IGNORECASE)
        
        if dependency_match:
            ids_str = dependency_match.group(1) # This is the string of IDs "1,2,3" or "1, 2, 3"
            parsed_ids = []
            if ids_str: # Ensure ids_str is not None or empty
                try:
                    parsed_ids = [int(id_val.strip()) for id_val in ids_str.split(',') if id_val.strip()]
                except ValueError:
                    # Log error or handle - some part of ids_str was not a valid int after split and strip.
                    # This case should be rare if the main regex is solid.
                    pass 
            
            self.depends_on_ids = parsed_ids
            if self.depends_on_ids:
                self.is_ready_to_schedule = False
            else:
                self.is_ready_to_schedule = True 

            # Remove the dependency string from the main description more robustly
            # This replaces the matched part (group(0)) and surrounding whitespace with a single space, then strips.
            self.description = re.sub(r"\s*" + re.escape(dependency_match.group(0)) + r"\s*", 
                                      " ", 
                                      self.description, 
                                      count=1, 
                                      flags=re.IGNORECASE).strip()

            # Re-parse tags if description was modified by dependency parsing
            self.tags = [] 
            m_tags_dependency_updated = re.findall(tag_re, self.description, re.U)
            for t_dep_u in m_tags_dependency_updated:
                self.tags.append(t_dep_u.lower())


    # def __str__(self):
    #     return self.description + ", " + str(self.prio) + ", " + str(self.duration)

    def __str__(self):
        return f"description: {self.description}, start_date: {self.start_date}, prio: {self.prio}"

    def __repr__(self):
        return self.__str__()
