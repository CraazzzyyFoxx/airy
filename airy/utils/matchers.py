import re

__all__ = ("ID_MATCHER",
           "ROLE_ID_MATCHER",
           "CHANNEL_ID_MATCHER",
           "MENTION_MATCHER",
           "URL_MATCHER",
           "EMOJI_MATCHER",
           "JUMP_LINK_MATCHER",
           "MODIFIER_MATCHER",
           "NUMBER_MATCHER",
           "ID_NUMBER_MATCHER",
           "START_WITH_NUMBER_MATCHER",
           "INVITE_MATCHER",
           "URL_MATCHER_2",
           "CUSTOM_EMOJI_MATCHER",
           "MESSAGE_LINK_MATCHER")

ID_MATCHER = re.compile("<@!?([0-9]{15,20})>")
ROLE_ID_MATCHER = re.compile("<@&([0-9]{15,20})>")
CHANNEL_ID_MATCHER = re.compile("<#([0-9]{15,20})>")
MENTION_MATCHER = re.compile("<@[!&]?\\d+>")
URL_MATCHER = re.compile(r'((?:https?://)[a-z0-9]+(?:[-._][a-z0-9]+)*\.[a-z]{2,5}(?::[0-9]{1,5})?(?:/[^ \n<>]*)?)', re.IGNORECASE)
EMOJI_MATCHER = re.compile('<(a?):([^: \n]+):([0-9]{15,20})>')
JUMP_LINK_MATCHER = re.compile(r"https://(?:canary|ptb)?\.?discord(?:app)?.com/channels/\d{15,20}/(\d{15,20})/(\d{15,20})")
MODIFIER_MATCHER = re.compile(r"^\[(.*):(.*)\]$")
NUMBER_MATCHER = re.compile(r"\d+")
ID_NUMBER_MATCHER = re.compile(r"\d{15,19}")
START_WITH_NUMBER_MATCHER = re.compile(r"^(\d+)")
INVITE_MATCHER = re.compile(
    r"(?:https?://)?(?:www\.)?(?:discord(?:\.| |\[?\(?\"?'?dot'?\"?\)?\]?)?(?:gg|io|me|li)|discord("
    r"?:app)?\.com/invite)/+((?:(?!https?)[\w\d-])+)",
    flags=re.IGNORECASE)

URL_MATCHER_2 = re.compile(r'https?://(www.)?[-a-zA-Z0-9а-яА-Я@:%.+~#=]{1,256}.[a-zA-ZА-Яа-я0-9()]{1,6}\b([-a-zA-Z0-9()@:%+.~#?&//=]*)')
CUSTOM_EMOJI_MATCHER = re.compile(r'<a?:[a-zA-Z0-9\_]+:([0-9]+)>')
MESSAGE_LINK_MATCHER = re.compile(
    r"https?:\/\/(www\.)?[-a-zA-Z0-9@:%._\+~#=]{1,256}\.[a-zA-Z0-9()]{1,6}\b([-a-zA-Z0-9()!@:%_\+.~#?&\/\/=]*)channels[\/][0-9]{1,}[\/][0-9]{1,}[\/][0-9]{1,}"
)