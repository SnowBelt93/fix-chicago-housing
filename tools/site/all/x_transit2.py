# Transit, Nov. 13, 2026: BRT and streetcar lines replace the buses on their street
from i18n_re import Q
T = {
    'fewer transit trips a weekday': ('viajes menos en transporte por día laborable', '工作日减少的公交出行', 'mniej przejazdów transportem w dzień roboczy'),
    'riders lose the bus between your stations': ('los pasajeros pierden el autobús entre tus estaciones', '乘客失去了你的车站之间的公交', 'pasażerowie tracą autobus między twoimi stacjami'),
    "It replaces the bus on its street, and its stations are far apart, so trips from the stops in between get slower. Add stations about every half mile, or run it more often.":
        ('Reemplaza el autobús de su calle y sus estaciones están lejos entre sí, así que los viajes desde las paradas intermedias se hacen más lentos. Agrega estaciones cada media milla, más o menos, o haz que pase más seguido.',
         '它取代了这条街上的公交，而车站间距又大，所以从中间站点出发的出行会变慢。大约每半英里设一个车站，或者提高班次。',
         'Zastępuje autobus na swojej ulicy, a jej stacje są daleko od siebie, więc przejazdy z przystanków pośrodku się wydłużają. Dodaj stacje mniej więcej co pół mili albo zwiększ częstotliwość.'),
}
R = [
    Q('{} trips a weekday would use it; {} of them already go by transit, many on the bus it replaces.',
      '{1} viajes por día laborable lo usarían; {2} de ellos ya van en transporte, muchos en el autobús que reemplaza.',
      '工作日约 {1} 人次会乘坐；其中 {2} 人次本来就乘公共交通，很多是坐它取代的公交。',
      '{1} przejazdów w dzień roboczy by z niej korzystało; {2} z nich już jedzie transportem, wielu autobusem, który zastępuje.'),
    Q('The {} stops running where it runs along this line: the {} replaces it there, so its riders take the new line instead and count as trips that already go by transit. Trips that get slower without the bus, like ones from a stop between two of your stations, count against the line.',
      'El {1} deja de circular donde va a lo largo de esta línea: el {2} lo reemplaza ahí, así que sus pasajeros toman la línea nueva y cuentan como viajes que ya van en transporte. Los viajes que se hacen más lentos sin el autobús, como los que salen de una parada entre dos de tus estaciones, cuentan en contra de la línea.',
      '{1}在沿这条线运行的路段停驶：由{2}取而代之，所以它的乘客改乘新线，算作本来就乘公共交通的出行。没有这路公交后变慢的出行，比如从你两个车站之间的站点出发的，会算作这条线的减分。',
      '{1} przestaje kursować tam, gdzie jedzie wzdłuż tej linii: zastępuje go tam {2}, więc jego pasażerowie przesiadają się na nową linię i liczą się jako przejazdy, które już odbywają się transportem. Przejazdy, które bez autobusu się wydłużają, np. z przystanku między dwiema twoimi stacjami, liczą się na niekorzyść linii.'),
    Q('The {} stop running where they run along this line: the {} replaces them there, so their riders take the new line instead and count as trips that already go by transit. Trips that get slower without the bus, like ones from a stop between two of your stations, count against the line.',
      'Los {1} dejan de circular donde van a lo largo de esta línea: el {2} los reemplaza ahí, así que sus pasajeros toman la línea nueva y cuentan como viajes que ya van en transporte. Los viajes que se hacen más lentos sin el autobús, como los que salen de una parada entre dos de tus estaciones, cuentan en contra de la línea.',
      '{1}在沿这条线运行的路段停驶：由{2}取而代之，所以它们的乘客改乘新线，算作本来就乘公共交通的出行。没有这些公交后变慢的出行，比如从你两个车站之间的站点出发的，会算作这条线的减分。',
      '{1} przestają kursować tam, gdzie jadą wzdłuż tej linii: zastępuje je tam {2}, więc ich pasażerowie przesiadają się na nową linię i liczą się jako przejazdy, które już odbywają się transportem. Przejazdy, które bez autobusu się wydłużają, np. z przystanku między dwiema twoimi stacjami, liczą się na niekorzyść linii.'),
]
