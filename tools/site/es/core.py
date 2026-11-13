# Shared header, menus, footer, feedback form, and patterns used on many pages.
# Words chosen once and used everywhere: ward = distrito, alderperson = concejal, City Council = Concejo Municipal,
# zoning = zonificación, rezoning = cambio de zonificación, permit = permiso, home(s) = vivienda(s), the L = el L, tú (not usted).
T = {
    'Shape Chicago tools': 'Herramientas de Shape Chicago',
    'Simulators': 'Simuladores', 'Housing': 'Vivienda', 'Transit': 'Transporte', 'Budget': 'Presupuesto', 'Pensions': 'Pensiones',
    'Bears stadium': 'Estadio de los Bears', 'Your lot': 'Tu lote', 'Plans people made': 'Planes de la gente',
    'Progress': 'Avances', 'Overview': 'Resumen', 'Homes': 'Viviendas', 'Zoning': 'Zonificación', 'Affordable': 'Asequible',
    'Rents and prices': 'Alquileres y precios', 'Streets': 'Calles', 'City money': 'Dinero de la ciudad', 'Big projects': 'Grandes proyectos',
    'In Springfield': 'En Springfield', 'Decisions coming up': 'Decisiones próximas', 'Your ward': 'Tu distrito', 'Your address': 'Tu dirección', 'Your address:': 'Tu dirección:', 'Zoning and rules': 'Zonificación y reglas', 'Grants and help': 'Ayudas y apoyo', 'Deal check': 'Análisis del proyecto', 'News': 'Noticias', 'Learn': 'Aprende',
    'Not affiliated with the City of Chicago.': 'Sin afiliación con la Ciudad de Chicago.',
    'Not affiliated with the City of Chicago, CTA, Metra or Pace.': 'Sin afiliación con la Ciudad de Chicago, la CTA, Metra ni Pace.',
    'Send feedback': 'Enviar comentarios', 'Feedback': 'Comentarios', 'Menu': 'Menú', 'Pages': 'Páginas', 'Close': 'Cerrar', 'All pages': 'Todas las páginas',
    'For media': 'Para medios', 'Support': 'Apoyar', 'Privacy': 'Privacidad', 'Terms': 'Términos',
    "Something wrong, confusing or missing? Say what you'd change.": '¿Algo está mal, confuso o falta? Dinos qué cambiarías.',
    'Your note': 'Tu nota', 'Send': 'Enviar',
    "Notes are anonymous, so we can't reply. Please leave out names and contact details.": 'Las notas son anónimas, así que no podemos responder. Por favor, no incluyas nombres ni datos de contacto.',
    "For example: the rent number on the housing page doesn't match the Sources tab.": 'Por ejemplo: el alquiler en la página de vivienda no coincide con la pestaña de fuentes.',
    'Write a few words first.': 'Escribe unas palabras primero.', 'Sending…': 'Enviando…', 'Sent. Thank you.': 'Enviado. Gracias.',
    "That's a lot of notes for one day. Try again tomorrow.": 'Son muchas notas para un día. Inténtalo mañana.',
    "That didn't send. Check your connection and try again.": 'No se envió. Revisa tu conexión e inténtalo de nuevo.',
    'Updated daily': 'Se actualiza a diario', 'New': 'Nuevo', 'Details': 'Detalles', 'Agenda': 'Agenda', 'Preview': 'Vista previa',
    'Sources': 'Fuentes', 'Sources:': 'Fuentes:', 'Share': 'Compartir', 'Start over': 'Empezar de nuevo', 'Previous': 'Anterior', 'Next': 'Siguiente',
    'Embed': 'Insertar', 'Copied': 'Copiado', 'Use my location': 'Usar mi ubicación', 'Pick a ward': 'Elige un distrito',
    'Embed this chart': 'Insertar este gráfico', 'Embed code': 'Código para insertar', 'Link to this chart': 'Enlace a este gráfico',
    'Copy embed code': 'Copiar código', 'Copy link': 'Copiar enlace',
    'Free to use with credit to Shape Chicago. It updates itself when the numbers change.': 'Uso libre citando a Shape Chicago. Se actualiza solo cuando cambian las cifras.',
    'More charts and how to cite them:': 'Más gráficos y cómo citarlos:', 'For media ›': 'Para medios ›',
    'Date passed': 'Fecha pasada', 'Today': 'Hoy', 'Tomorrow': 'Mañana', 'Passed': 'Pasó',
    'About': 'Acerca de', 'Grants finder': 'Buscador de ayudas', 'Affordable deal check': 'Análisis de proyecto asequible',
    'Endorse': 'Respaldar', 'See the plan': 'Ver el plan', 'All plans': 'Todos los planes',
}
H = {}
HR = []
# month and day names, looked up inside patterns as {{Nov}} (shape.js)
W = {'January': 'enero', 'February': 'febrero', 'March': 'marzo', 'April': 'abril', 'May': 'mayo', 'June': 'junio', 'July': 'julio', 'August': 'agosto',
     'September': 'septiembre', 'October': 'octubre', 'November': 'noviembre', 'December': 'diciembre',
     'Jan': 'ene.', 'Feb': 'feb.', 'Mar': 'mar.', 'Apr': 'abr.', 'Jun': 'jun.', 'Jul': 'jul.', 'Aug': 'ago.', 'Sep': 'sept.', 'Sept': 'sept.', 'Oct': 'oct.', 'Nov': 'nov.', 'Dec': 'dic.',
     'Monday': 'lunes', 'Tuesday': 'martes', 'Wednesday': 'miércoles', 'Thursday': 'jueves', 'Friday': 'viernes', 'Saturday': 'sábado', 'Sunday': 'domingo',
     'Mon': 'lun.', 'Tue': 'mar.', 'Wed': 'mié.', 'Thu': 'jue.', 'Fri': 'vie.', 'Sat': 'sáb.', 'Sun': 'dom.'}
MF = '(January|February|March|April|May|June|July|August|September|October|November|December)'
MS = '(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sept|Sep|Oct|Nov|Dec)\\.?'
MA = '(January|February|March|April|May|June|July|August|September|October|November|December|Jan|Feb|Mar|Apr|Jun|Jul|Aug|Sept|Sep|Oct|Nov|Dec)\\.?'
DF = '(Monday|Tuesday|Wednesday|Thursday|Friday|Saturday|Sunday)'
DS = '(Mon|Tue|Wed|Thu|Fri|Sat|Sun)'
R = [
    [f'^{DF}, {MF} (\\d+)$', '{{$1}} $3 de {{$2}}'],
    [f'^{MA} (\\d+), (\\d{{4}})$', '$2 de {{$1}} de $3'],
    [f'^{MA} (\\d+)$', '$2 de {{$1}}'],
]
R += [
    ['^Ward (\\d+)$', 'Distrito $1'],
    ['^Ward (\\d+) news feed$', 'Noticias del distrito $1'],
    ['^Following Ward (\\d+)$', 'Sigues el distrito $1'],
    ['^Ald\\. (.+)$', 'Concejal $1'],
    ['^Alderperson (.+)$', 'Concejal $1'],
    ['^Email Ald\\. (.+)$', 'Escribe a $1'],
    ['^In (\\d+) days$', 'En $1 días'],
    ['^Updated (.+)$', 'Actualizado: $1'],
    ['^Endorse this plan\\. (\\d+) endorsements?$', 'Respaldar este plan. $1 respaldos'],
    ['^\\+(\\d+) more$', '+$1 más'],
    ['^By (.+) from (.+) · today$', 'De $1, de $2 · hoy'],
    ['^By (.+) · today$', 'De $1 · hoy'],
    ['^From a neighbor · today$', 'De un vecino · hoy'],
    ['^From a neighbor · (.+)$', 'De un vecino · $1'],
    ['^The (.+) Plan$', 'El plan $1'],
    ['^Plan number (\\d+)$', 'Plan número $1'],
    ['^(\\d[\\d,]*) homes$', '$1 viviendas'],
]
