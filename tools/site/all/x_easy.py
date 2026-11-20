# Nov. 20, 2026: housing "That's it? Yep." note, and the new home page.
from i18n_re import P, Q
T = {
    "That's it? Yep.": ('¿Eso es todo? Sí.', '就这样？没错。', 'To wszystko? Tak.'),
    'On paper, that was easy.': ('En papel, fue fácil.', '纸面上，这很简单。', 'Na papierze to było łatwe.'),
    "That's the point: Chicago's shortage isn't a mystery, and zoning is the cheap part of fixing it.": ('De eso se trata: la escasez de Chicago no es un misterio, y la zonificación es la parte barata de resolverla.', '这正是重点：芝加哥的住房短缺并不神秘，而分区规划是解决它最便宜的部分。', 'O to chodzi: niedobór mieszkań w Chicago nie jest tajemnicą, a strefowanie to najtańsza część jego rozwiązania.'),
    "The hard part is what this map can't do for you: 26 votes on the City Council, neighbors at every hearing, and builders who can make the numbers work at today's interest rates.": ('La parte difícil es lo que este mapa no puede hacer por ti: 26 votos en el Concejo Municipal, vecinos en cada audiencia y constructores a quienes les salgan las cuentas con las tasas de interés de hoy.', '难的是这张地图帮不了你的部分：市议会的26票、每场听证会上的邻居，以及在当今利率下能算得过账的建造商。', 'Trudne jest to, czego ta mapa za ciebie nie zrobi: 26 głosów w Radzie Miasta, sąsiedzi na każdym przesłuchaniu i deweloperzy, którym rachunki zgadzają się przy dzisiejszych stopach procentowych.'),
    'Want a real challenge?': ('¿Quieres un reto de verdad?', '想要真正的挑战吗？', 'Chcesz prawdziwego wyzwania?'),
    "Chicago covers the whole region's gap": ('Chicago cubre toda la escasez de la región', '芝加哥承担整个地区的缺口', 'Chicago pokrywa niedobór całego regionu'),
    'Try Every ward': ('Prueba Cada distrito', '试试“每个选区”', 'Spróbuj Każdy okręg'),
    'Every ward has to zone its share': ('Cada distrito tiene que zonificar su parte', '每个选区都必须规划自己的份额', 'Każdy okręg musi przeznaczyć swoją część'),
    'Keep going': ('Seguir', '继续', 'Dalej'),
    'Run your plan to 2041': ('Lleva tu plan hasta 2041', '把你的方案运行到2041年', 'Przeprowadź swój plan do 2041'),
}
R = [
    Q("You let {#}% of Chicago's lots hold more homes, and that covers the city's share of the shortage by 2041.",
      'Permitiste que el {1} % de los lotes de Chicago tengan más viviendas, y eso cubre la parte de la ciudad de la escasez hasta 2041.',
      '你让芝加哥{1}%的地块可以容纳更多住房，这就覆盖了该市到2041年应承担的短缺份额。',
      'Pozwoliłeś, by {1}% działek w Chicago mieściło więcej mieszkań, i to pokrywa udział miasta w niedoborze do 2041.'),
]
