"""Constants of the Xiaomi Aqara Lock."""

WITH_LI_BATTERY = 1
SUPPORT_ALARM = 2
SUPPORT_DOORBELL = 4
SUPPORT_CAMERA = 8
SUPPORT_WIFI = 16

DEVICE_MAPPINGS = {
    "lumi.lock.aq1": SUPPORT_ALARM,
    "lumi.lock.acn02": SUPPORT_ALARM | SUPPORT_DOORBELL,
    "lumi.lock.acn03": SUPPORT_ALARM | SUPPORT_DOORBELL,
    "aqara.lock.eicn01": SUPPORT_ALARM | SUPPORT_DOORBELL,
    "aqara.lock.acn001": SUPPORT_ALARM | SUPPORT_DOORBELL,
    "aqara.lock.acn004": (
        WITH_LI_BATTERY | SUPPORT_ALARM |
        SUPPORT_DOORBELL | SUPPORT_WIFI),
    "aqara.lock.acn005": (
        WITH_LI_BATTERY | SUPPORT_ALARM |
        SUPPORT_DOORBELL | SUPPORT_WIFI),
    "aqara.lock.wbzac1": (
        WITH_LI_BATTERY | SUPPORT_ALARM |
        SUPPORT_DOORBELL | SUPPORT_WIFI | SUPPORT_CAMERA),
    "aqara.lock.bzacn3": (
        SUPPORT_ALARM | SUPPORT_DOORBELL),
    "aqara.lock.bzacn4": (
        SUPPORT_ALARM | SUPPORT_DOORBELL),
    "aqara.lock.dacn03": (
        WITH_LI_BATTERY | SUPPORT_ALARM |
        SUPPORT_DOORBELL | SUPPORT_WIFI | SUPPORT_CAMERA),
    "aqara.lock.acn002": (
        WITH_LI_BATTERY | SUPPORT_ALARM |
        SUPPORT_DOORBELL | SUPPORT_WIFI | SUPPORT_CAMERA),
    "aqara.lock.agl002": SUPPORT_ALARM | SUPPORT_DOORBELL
}

LOCK_NOTIFICATION = {
    "latch_state": {
        "default": "Latch state changed",
        "0": "Remove the locking from inside",
        "1": "Reverse locked"},
    "lock": {
        "default": "Lock state changed",
        "0": "Door is open",
        "1": "Door is closed",
        "2": "Door is not close",
        "3": "Doorbell is ringing",
        "4": "Lock is damaged",
        "5": "Door is conceal",
        "6": "Other 1",
        "7": "Other 2"},
    "door": {
        "default": "door state changed",
        "0": "Unknown",
        "1": "The door cannot be locked",
        "2": "The door is not closed",
        "3": "The door is not locked",
        "4": "The door is locked",
        "5": "The door is auti-locked",
        "6": "The door is unlocked",
        "7": "The door is locked and auti-locked",
        "8": "The door is left unlocked"},
    "lock_event": {
        "default": "Got lock event",
        "0": "Unlock",
        "1": "Lock"
    },
    "unlock from inside": {"default": "Unlock from Inside"},
    "someone detected": {"default": "Someone is lingering at the door"},
    "li battery notify":
        {"default": "Li Battery notify",
            "0": "Li Battery is abnormal",
            "1": "Li Battery is normal"},
    "battery notify":
        {"default": "Battery notify",
            "0": "Battery is die",
            "1": "Battery level is low",
            "2": "Battery level is middle",
            "3": "Battery level is full"},
    "camera connected": {"default": "Camera is connected"},
    "open in away mode": {
        "default":
            "In the Away-from-home Mode, someone opens the door indoors"},
    "lock by handle": {"default": "Lock by door handle"},
    "unlock by password": {"default": "Unlocked with Keypad by user"},
    "unlock by fingerprint": {"default": "Unlocked with Fingerprint by user"},
    "unlock by bluetooth": {"default": "Unlocked with Bluetooth by user"},
    "unlock by homekit": {"default": "Unlocked with HomeKit by user"},
    "unlock by key": {"default": "Unlocked with key by user"},
    "unlock by nfc": {"default": "Unlocked with NFC by user"},
    "unlock by face": {"default": "Unlocked with Face by user"},
    "unlock by temporary password": {"default": "Unlocked with Temporary Password"},
    "away mode": {
        "default": "Away mode changed",
        "0": "Away-from-home mode is removed",
        "1": "Away-from-home mode is enabled"},
    "nfc added": {"default": "Added NFC card or Tag"},
    "nfc removed": {"default": "Removed NFC card or Tag"},
    "verification failed": {
        "default": "door lock verifications failed",
        "3235774464": "Frequent door opening failures due to incorrect passwords",
        "3235774465": "Frequent door opening failures due to incorrect fingerprints",
        "3235774469": "Frequent door openings with abnormal keys",
        "3235774470": "Foreign objects in the keyhole",
        "3235774471": "Keys not removed",
        "3235774472": "Frequent door opening failures with incorrect NFC",
        "3235774473": "Door unlocked after timeout",
        "3235774474": "Multiple verification failures (advanced protection)",
        "3235778564": "Automatic lock body abnormal"},
    "user added": {
        "default": "Add User"},
    "user removed": {
        "default": "Remove User"},
    "all user removed": {
        "default": "Remove All User"},
}
