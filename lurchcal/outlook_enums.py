# - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
# Copyright (C) 2023-2024 theoky
# - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
"""
"""

from enum import Enum


# https://learn.microsoft.com/en-us/office/vba/api/outlook.appointmentitem.busystatus
class OlBusyStatus(Enum):
    olBusy = 2  # The user is busy.
    olFree = 0  # The user is available.
    olOutOfOffice = 3  # The user is out of office.
    olTentative = 1  # The user has a tentative appointment scheduled.
    olWorkingElsewhere = 4  # The user is working in a location away from the office.


# https://learn.microsoft.com/en-us/office/vba/api/outlook.oluserpropertytype
class OlUserPropertyType(Enum):
    olCombination = 19  # The property type is a combination of other types. It corresponds to the MAPI type PT_STRING8.
    olCurrency = 14  # Represents a Currency property type. It corresponds to the MAPI type PT_CURRENCY.
    olDateTime = 5  # Represents a DateTime property type. It corresponds to the MAPI type PT_SYSTIME.
    olDuration = 7  # Represents a time duration property type. It corresponds to the MAPI type PT_LONG.
    olEnumeration = 21  # Represents an enumeration property type. It corresponds to the MAPI type PT_LONG.
    olFormula = 18  # Represents a formula property type. It corresponds to the MAPI type PT_STRING8. See UserDefinedProperty.Formula property.
    olInteger = 20  # Represents an Integer number property type. It corresponds to the MAPI type PT_LONG.
    olKeywords = 11  # Represents a String array property type used to store keywords. It corresponds to the MAPI type PT_MV_STRING8.
    olNumber = 3  # Represents a Double number property type. It corresponds to the MAPI type PT_DOUBLE.
    olOutlookInternal = 0  # Represents an Outlook internal property type.
    olPercent = 12  # Represents a Double number property type used to store a percentage. It corresponds to the MAPI type PT_LONG.
    olSmartFrom = 22  # Represents a smart from property type. This property indicates that if the From property of an Outlook item is empty, then the To property should be used instead.
    olText = 1  # Represents a String property type. It corresponds to the MAPI type PT_STRING8.
    olYesNo = 6  # Represents a yes/no (Boolean) property type. It corresponds to the MAPI type PT_BOOLEAN.


# https://learn.microsoft.com/en-us/office/vba/api/outlook.olmeetingstatus
class OlMeetingStatus(Enum):
    olMeeting = 1  # The meeting has been scheduled.
    olMeetingCanceled = 5  # The scheduled meeting has been cancelled.
    olMeetingReceived = 3  # The meeting request has been received.
    olMeetingReceivedAndCanceled = 7  # The scheduled meeting has been cancelled but still appears on the user's calendar.
    olNonMeeting = 0  # An Appointment item without attendees has been scheduled. This status can be used to set up holidays on a calendar.


class OlSensitivity(Enum):
    olConfidential = 3  # Confidential
    olNormal = 0  # Normal sensitivity
    olPersonal = 1  # Personal
    olPrivate = 2  # Private
