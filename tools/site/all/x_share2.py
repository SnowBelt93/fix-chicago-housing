# Nov. 16, 2026: the budget's "Share or save" button and dialog.
from i18n_re import P, Q
T = {
    'Share or save': ('Compartir o guardar', '分享或保存', 'Udostępnij lub zapisz'),
    'Share or save this budget': ('Compartir o guardar este presupuesto', '分享或保存这份预算', 'Udostępnij lub zapisz ten budżet'),
    'Balanced.': ('Equilibrado.', '已平衡。', 'Zrównoważony.'),
    'Send a link': ('Enviar un enlace', '发送链接', 'Wyślij link'),
    'The link holds every choice you made. Anyone who opens it sees your budget and can change it.': (
        'El enlace guarda cada decisión que tomaste. Quien lo abra verá tu presupuesto y podrá cambiarlo.',
        '链接保存了你做的每一个选择。打开链接的人都能看到你的预算，也可以修改。',
        'Link zawiera każdy Twój wybór. Każdy, kto go otworzy, zobaczy Twój budżet i będzie mógł go zmienić.'),
    'Only on this device. Your last budget also comes back when you return.': (
        'Solo en este dispositivo. Tu último presupuesto también vuelve cuando regresas.',
        '仅保存在这台设备上。你下次回来时，上一次的预算也会自动恢复。',
        'Tylko na tym urządzeniu. Twój ostatni budżet wróci też, gdy tu wrócisz.'),
    'Post it to Plans people made': ('Publícalo en Planes de la gente', '发布到“大家做的方案”', 'Opublikuj w Planach innych'),
    'Others can see it, endorse it and open it.': ('Otras personas pueden verlo, respaldarlo y abrirlo.', '其他人可以查看、支持并打开它。', 'Inni mogą go zobaczyć, poprzeć i otworzyć.'),
    'See the budgets people shared': ('Ver los presupuestos que compartió la gente', '查看大家分享的预算', 'Zobacz budżety udostępnione przez innych'),
    'Name this budget': ('Ponle nombre a este presupuesto', '给这份预算起个名字', 'Nazwij ten budżet'),
}
R = [
    Q('Balanced, with {#} to spare.', 'Equilibrado, con {1} de sobra.', '已平衡，还多出 {1}。', 'Zrównoważony, z nadwyżką {1}.'),
    Q('{#} still to close.', 'Faltan {1} por cerrar.', '还差 {1} 需要弥补。', 'Zostało {1} do zamknięcia.'),
]
