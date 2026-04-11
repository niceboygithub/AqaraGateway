"""Local WAV playback on Realtek Aqara gateways (telnet + aplay)."""
import logging
import re
from typing import TYPE_CHECKING

from .utils import Utils

if TYPE_CHECKING:
    from .gateway import Gateway

_LOGGER = logging.getLogger(__name__)

MUSIC_SCENE_DIR = "/data/musics/music-scene"

# 0 = весь WAV; иначе секунды: aplay -d N
SPEAKER_APLAY_MAX_DURATION_SEC = 0

SPEAKER_SOUND_CHOICES: tuple[tuple[str, str], ...] = (
    ("Doorbell 1", "door_bell_1.wav"),
    ("Doorbell 2", "door_bell_2.wav"),
    ("Doorbell 3", "door_bell_3.wav"),
    ("Doorbell 4", "door_bell_4.wav"),
    ("Alarm default", "alarm.wav"),
    ("Alarm 1", "alarm_1.wav"),
    ("Alarm 2", "alarm_2.wav"),
    ("Alarm 3", "alarm_3.wav"),
    ("Alarm 4", "alarm_4.wav"),
    ("Alarm 5", "alarm_5.wav"),
    ("Alarm 6", "alarm_6.wav"),
    ("Alarm 7", "alarm_7.wav"),
    ("Alarm 8", "alarm_8.wav"),
    ("Alarm 9", "alarm_9.wav"),
    ("Arm OK", "arm_ok.wav"),
    ("Arm start", "arm_start.wav"),
    ("Disarm", "disarm.wav"),
    ("Welcome 1", "welcome_1.wav"),
    ("Welcome 2", "welcome_2.wav"),
    ("Welcome 3", "welcome_3.wav"),
    ("Welcome 4", "welcome_4.wav"),
    ("Welcome 5", "welcome_5.wav"),
    ("Welcome 6", "welcome_6.wav"),
    ("Welcome 7", "welcome_7.wav"),
    ("Welcome 8", "welcome_8.wav"),
    ("Welcome 9", "welcome_9.wav"),
    ("Welcome 10", "welcome_10.wav"),
    ("Clock", "clock.wav"),
)

SPEAKER_LABEL_TO_FILE = dict(SPEAKER_SOUND_CHOICES)
SPEAKER_OPTIONS = [label for label, _ in SPEAKER_SOUND_CHOICES]


def _aplay_duration_args() -> str:
    n = int(SPEAKER_APLAY_MAX_DURATION_SEC)
    if n <= 0:
        return ""
    return f" -d {n}"


def _safe_wav_name(filename: str) -> bool:
    if not filename or len(filename) > 64:
        _LOGGER.debug("reject wav: empty or len>64 (%r)", filename)
        return False
    if not re.fullmatch(r"[a-zA-Z0-9_.-]+\.wav", filename):
        _LOGGER.debug("reject wav: bad pattern (%r)", filename)
        return False
    return True


def play_speaker_scene(gateway: "Gateway", wav_filename: str) -> None:
    """Telnet: login, один shell-ряд killall + aplay в фоне, close."""
    host = getattr(gateway, "host", "?")
    _LOGGER.info("play_speaker_scene start host=%s wav=%r", host, wav_filename)

    if not _safe_wav_name(wav_filename):
        _LOGGER.error(
            "play_speaker_scene aborted: invalid wav (%r) host=%s",
            wav_filename,
            host,
        )
        return

    shell = None
    try:
        try:
            gw_dev = gateway.device
            model = gw_dev.get("model", "?")
        except Exception as err:
            _LOGGER.exception(
                "play_speaker_scene: gateway.device failed host=%s: %s",
                host,
                err,
            )
            return

        device_name = Utils.get_device_name(model).lower()
        _LOGGER.debug(
            "play_speaker_scene model=%r device_name=%r", model, device_name
        )

        shell = gateway._get_shell(device_name)
        shell.login()
        _LOGGER.debug("play_speaker_scene login OK host=%s", host)

        dur = _aplay_duration_args()
        path = f"{MUSIC_SCENE_DIR}/{wav_filename}"
        # Один round-trip после логина: остановить старый aplay и запустить новый.
        cmd = (
            f"killall -9 aplay 2>/dev/null; sleep 0.05; "
            f"/bin/aplay -q{dur} {path} & true"
        )
        _LOGGER.info("play_speaker_scene cmd=%r host=%s", cmd, host)
        out = shell.run_command(cmd, read_timeout=20)
        tail = (out or "")[-400:]
        _LOGGER.debug(
            "play_speaker_scene result len=%s tail=%r host=%s",
            len(out or ""),
            tail,
            host,
        )
        if out and (
            "error" in out.lower()
            or "cannot" in out.lower()
            or "no such" in out.lower()
        ):
            _LOGGER.warning(
                "play_speaker_scene output suspicious host=%s tail=%r",
                host,
                tail,
            )

        _LOGGER.info("play_speaker_scene OK host=%s wav=%r", host, wav_filename)
    except Exception:
        _LOGGER.exception(
            "play_speaker_scene FAILED host=%s wav=%r", host, wav_filename
        )
    finally:
        if shell is not None:
            try:
                shell.close()
            except Exception as err:
                _LOGGER.warning(
                    "play_speaker_scene shell.close error host=%s: %s",
                    host,
                    err,
                )
