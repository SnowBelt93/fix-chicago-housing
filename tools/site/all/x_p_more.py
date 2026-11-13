# Progress: small pieces found in the second pass
from i18n_re import P
T = {
    'Two miles of rebuilt track, four rebuilt stations and the bypass at Belmont. Builders reported the main work finished July 1, 2026': ('Dos millas de vía reconstruida, cuatro estaciones reconstruidas y el desvío de Belmont. Los constructores informaron que la obra principal terminó el 1 de julio de 2026', '重建了两英里轨道、四座车站和 Belmont 绕行线。施工方报告主体工程于 2026 年 7 月 1 日完工', 'Dwie mile przebudowanego toru, cztery przebudowane stacje i bypass przy Belmont. Wykonawcy zgłosili zakończenie głównych prac 1 lipca 2026'),
}
R = [
    P('Rides: federal monthly count through Sept. 2026, checked every morning · yearly totals through 2025 · projects as of June to Aug. 2026 · checked Nov. 9, 2026', 'Viajes: conteo mensual federal hasta @1, revisado cada mañana · totales anuales hasta #2 · proyectos de junio a @3 · revisado el @4', '乘车人次：联邦月度统计截至 @1，每天早上检查 · 年度总数截至 #2 年 · 项目信息为 6 月至 @3 · 核查于 @4', 'Przejazdy: federalne dane miesięczne do @1, sprawdzane co rano · sumy roczne do #2 · projekty od czerwca do @3 · sprawdzono @4'),
    P('of $75M in ward street money committed by Sept. 30, 2026', 'de los #1 de dinero de calles de distrito comprometidos hasta el @2', '（#1 选区街道资金中截至 @2 已承诺的部分）', 'z #1 pieniędzy ulicznych okręgów rozdysponowano do @2'),
    P('8,900 needed by now', '#1 necesarias hasta ahora', '目前需要 #1 套', '#1 potrzebnych do tej pory'),
    P('of 2025’s zoning changes for new homes had a building permit within a year', 'de los cambios de zonificación de #1 para viviendas nuevas tuvo permiso de construcción en un año', '#1 年的新建住房分区变更在一年内获得了建筑许可', 'zmian strefowania z #1 dla nowych mieszkań dostało pozwolenie budowlane w ciągu roku'),
    P('The highest since 2021', 'La más alta desde #1', '#1 年以来最高', 'Najwięcej od #1'),
    P('The best year was 2025 since 2021', 'El mejor año fue #1 desde #2', '#2 年以来最好的一年是 #1 年', 'Najlepszy rok od #2 to #1'),
    ['^A bill is listed if what it amends \\(the Illinois Compiled Statutes sections\\) or its synopsis is about zoning and housing, the transit agencies, Chicago’s taxes and budget, the four city pension funds, or property taxes in Cook County\\. Some listed bills only touch a topic in passing; bills that change only a title or make technical changes are left out\\. Stages come from each bill’s list of actions\\.$',
     'Un proyecto aparece si lo que modifica (secciones de los Estatutos Compilados de Illinois) o su resumen trata de zonificación y vivienda, las agencias de transporte, los impuestos y el presupuesto de Chicago, los cuatro fondos de pensiones de la ciudad o el impuesto predial en el condado de Cook. Algunos solo tocan un tema de pasada; se excluyen los que solo cambian un título o hacen cambios técnicos. Las etapas vienen de la lista de acciones de cada proyecto.',
     '如果法案修改的内容（伊利诺伊州汇编法规条文）或其摘要涉及分区和住房、交通机构、芝加哥的税收和预算、四个市养老基金或库克县房产税，就会列入。有些法案只是顺带涉及；只改标题或作技术性修改的法案不列入。阶段依据每项法案的动作清单。',
     'Projekt jest na liście, jeśli to, co zmienia (przepisy Illinois Compiled Statutes), lub jego opis dotyczy strefowania i mieszkań, przewoźników, podatków i budżetu Chicago, czterech miejskich funduszy emerytalnych lub podatków od nieruchomości w hrabstwie Cook. Niektóre tylko ocierają się o temat; pomijamy te, które zmieniają tylko tytuł lub wprowadzają zmiany techniczne. Etapy pochodzą z listy działań każdego projektu.'],
]
