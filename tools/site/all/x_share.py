# The share box, delete and report buttons every simulator uses (shape/plans.js), and the server's name messages
from i18n_re import P, Q
T = {
    'Name your plan': ('Ponle nombre a tu plan', '给方案起个名字', 'Nazwij swój plan'), 'Suggest a name': ('Sugerir un nombre', '推荐一个名字', 'Zaproponuj nazwę'),
    'Your name': ('Tu nombre', '你的名字', 'Twoje imię'), '(optional)': ('(opcional)', '（可选）', '(opcjonalnie)'), 'A first name or nickname': ('Un nombre de pila o apodo', '名字或昵称', 'Imię lub pseudonim'),
    "Don't use your full name. Names with swearing, insults, links or contact details are turned away.": ('No uses tu nombre completo. Se rechazan los nombres con groserías, insultos, enlaces o datos de contacto.', '不要用全名。含脏话、侮辱、链接或联系方式的名字会被拒绝。', 'Nie podawaj pełnego imienia i nazwiska. Nazwy z wulgaryzmami, obelgami, linkami lub danymi kontaktowymi są odrzucane.'),
    'Share it on Plans people made': ('Compártelo en Planes de la gente', '分享到大家的方案', 'Udostępnij w Planach mieszkańców'), 'Shared': ('Compartido', '已分享', 'Udostępniono'), 'Sharing…': ('Compartiendo…', '正在分享…', 'Udostępnianie…'),
    "There's nothing to share yet. Make a change first.": ('Aún no hay nada que compartir. Haz un cambio primero.', '还没有可分享的内容。先做些改动。', 'Nie ma jeszcze czego udostępnić. Najpierw coś zmień.'),
    'Give the plan a name of at least 3 characters.': ('Dale al plan un nombre de al menos 3 caracteres.', '方案名字至少 3 个字符。', 'Nadaj planowi nazwę z co najmniej 3 znaków.'),
    'Your name needs at least 2 characters, or leave it empty.': ('Tu nombre necesita al menos 2 caracteres, o déjalo vacío.', '你的名字至少 2 个字符，或者留空。', 'Imię musi mieć co najmniej 2 znaki albo zostaw puste.'),
    "That's a lot of plans for one day. Try again tomorrow.": ('Son muchos planes para un solo día. Intenta mañana.', '一天分享的方案太多了，明天再试。', 'To dużo planów jak na jeden dzień. Spróbuj jutro.'),
    'Try another name.': ('Prueba otro nombre.', '换个名字试试。', 'Spróbuj innej nazwy.'), "Couldn't reach the plan gallery. Try again in a bit.": ('No se pudo conectar con la galería de planes. Intenta de nuevo en un rato.', '无法连接方案库，请稍后再试。', 'Nie udało się połączyć z galerią planów. Spróbuj za chwilę.'),
    'See it on Plans people made': ('Velo en Planes de la gente', '在大家的方案中查看', 'Zobacz w Planach mieszkańców'),
    'Delete this plan': ('Borrar este plan', '删除这个方案', 'Usuń ten plan'), 'Delete it for good?': ('¿Borrarlo para siempre?', '永久删除？', 'Usunąć na zawsze?'), 'Yes, delete': ('Sí, borrar', '是，删除', 'Tak, usuń'), 'Keep it': ('Conservarlo', '保留', 'Zostaw'),
    'Deleting…': ('Borrando…', '正在删除…', 'Usuwanie…'), "This browser can't delete that plan.": ('Este navegador no puede borrar ese plan.', '这个浏览器不能删除该方案。', 'Ta przeglądarka nie może usunąć tego planu.'),
    "Deleted. It's gone from Plans people made.": ('Borrado. Ya no está en Planes de la gente.', '已删除。它已从大家的方案中移除。', 'Usunięto. Zniknął z Planów mieszkańców.'),
    'Report this name': ('Reportar este nombre', '举报这个名字', 'Zgłoś tę nazwę'), 'Thanks. Names that several people report are hidden.': ('Gracias. Los nombres que reportan varias personas se ocultan.', '谢谢。被多人举报的名字会被隐藏。', 'Dzięki. Nazwy zgłoszone przez kilka osób są ukrywane.'),
    "Couldn't send that. Try again in a bit.": ('No se pudo enviar. Intenta de nuevo en un rato.', '发送失败，请稍后再试。', 'Nie udało się wysłać. Spróbuj za chwilę.'),
    "Keep the plan's name between 3 and 60 characters.": ('El nombre del plan debe tener entre 3 y 60 caracteres.', '方案名字须在 3 到 60 个字符之间。', 'Nazwa planu musi mieć od 3 do 60 znaków.'), 'Keep your name between 2 and 24 characters.': ('Tu nombre debe tener entre 2 y 24 caracteres.', '你的名字须在 2 到 24 个字符之间。', 'Imię musi mieć od 2 do 24 znaków.'),
    "Names can't include links, emails, handles or phone numbers.": ('Los nombres no pueden incluir enlaces, correos, usuarios ni teléfonos.', '名字不能包含链接、邮箱、账号或电话号码。', 'Nazwy nie mogą zawierać linków, e-maili, nazw kont ani numerów telefonów.'),
    "Names can't make a plan look like it comes from the city.": ('Los nombres no pueden hacer parecer que el plan viene de la ciudad.', '名字不能让方案看起来像来自市政府。', 'Nazwy nie mogą sugerować, że plan pochodzi od miasta.'), "That name isn't allowed here. Try another.": ('Ese nombre no está permitido aquí. Prueba otro.', '这里不允许这个名字，换一个吧。', 'Ta nazwa jest tu niedozwolona. Spróbuj innej.'),
    'Try a name without long runs of the same character.': ('Prueba un nombre sin tantas repeticiones del mismo carácter.', '换个不含一长串相同字符的名字。', 'Spróbuj nazwy bez długich ciągów tego samego znaku.'), 'Use letters, numbers, spaces and simple punctuation only.': ('Usa solo letras, números, espacios y puntuación simple.', '只能用字母、数字、空格和简单标点。', 'Używaj tylko liter, cyfr, spacji i prostej interpunkcji.'),
    'Shared as': ('Compartido como', '已分享为', 'Udostępniono jako'),
}
R = [
    Q('by {}.', 'por {1}.', '，作者 {1}。', 'autor: {1}.'),
]
