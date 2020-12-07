from collections import defaultdict
import requests
import pickle
import matplotlib
import matplotlib.pyplot as plt
from dateutil.parser import parse as parseDate
from pylatex import Document, Section, Subsection, Tabular, Figure, Center, Package, Command
from pylatex.utils import NoEscape, bold, italic

# This script generates a report from a Zetkin survey.
# 
# It most definitely is buggy but worked for us with these settings. The script hastily written and can surely be improved.
#
# IMPORTANT: If not anonymized, the report can contain personal information and should be treated according to the GDPR.
# The cached data also contains personal information regardless of the anonymization setting.
# Make sure that all the generated files are either deleted (don't put in trash) or kept on secure storage according to the GDPR
# Document when any copies are made so that data can be retreived/deleted/updated when we are asked to do so.
#
# To access data from Zetkin we need an authorization key that you can get like this:
# 1. Log in to zetkin
# 2. Open dev tools in chrome, network tab, clear
# 3. Load survey subissions
# 4. Look under 'surveys' request (might be more than one, check another if next step is missing)
# 5. Under Headers/request-headers find 'Authorization: Bearer ************'
# 6. Copy ************ to auth below

#### settings ####

auth = ''
organizationId = '359'  # These two values are found in the url when browsing the survey of interest
surveyId = '307'
author = u'Vänsterpartiet Västra Södermalm'
anonymize = False

# This is used to filter out board members and test submissions
exclude = []

# Members will be categorized by what option they chose for this question.
categorizeBy = 2562

saveCache = True
useCache = False #set to false after first run to use cache instead of downloading data from zetkin

#### program code ####

histogramFilename = 'figs/submissionsByDate.pdf'
url = 'https://api.zetk.in/v1'

if useCache:
	with open('cache', 'rb') as f:
		survey, submissions, responses = pickle.load(f)
else:
	header = {'Authorization': 'Bearer '+auth}

	req = url+'/orgs/{}/surveys/{}'.format(organizationId, surveyId)
	survey = requests.get(req, headers = header).json()['data']

	req = url+'/orgs/{}/surveys/{}/submissions'.format(organizationId, surveyId)
	submissions = requests.get(req, headers = header).json()['data']

	responses={}
	for s in submissions:
		req = url+'/orgs/{}/survey_submissions/{}'.format(organizationId, s['id'])
		responses[s['id']] = requests.get(req, headers = header).json()['data']['responses']	

	if saveCache:
		with open('cache', 'wb') as f:
			pickle.dump((survey, submissions, responses), f)

q = [e for e in survey['elements'] if e['id']==categorizeBy][0]['question']
cats = [o['id'] for o in q['options']]
catNames = {o['id']:o['text'] for o in q['options']}

members = {}
for s in submissions:
	members[s['id']] = s['respondent']

for e in exclude:
	if members[e]:
		print('Excluding: {}, {}'.format(members[e]['first_name'], members[e]['last_name']))
	else:
		print('Excluding anonymous submission')

def name(m):
	return m['first_name']+', '+m['last_name'] if m else 'Anonym'

# now remove exlusions
submissions = [s for s in submissions if s['id'] not in exclude]
responses = {i:r for i,r in responses.items() if i not in exclude}

catMembers = defaultdict(list)
textResponsesByQuestion = defaultdict(list)
optionResponsesByQuestion = defaultdict(lambda: defaultdict(int))
catOptionResponsesByQuestion = [defaultdict(lambda: defaultdict(int)) for i in range(len(cats))]
for id, r in responses.items():
	if categorizeBy:
		cat = [qr['options'] for qr in r if qr['question_id']==categorizeBy]
		if len(cat)==1:
			cat=cats.index(cat[0][0])
		else: cat = None
		catMembers[cat].append(id)
	for qr in r:
		if 'response' in qr:
			textResponsesByQuestion[qr['question_id']].append((id, qr['response']))
		else:
			for o in qr['options']:
				optionResponsesByQuestion[qr['question_id']][o] += 1
				if categorizeBy and not cat is None:
					catOptionResponsesByQuestion[cat][qr['question_id']][o] += 1

# The below was used to generate excel sheet with numbers for us to call some of the respondents
# with open('toCall.csv','w+') as f:
# 	for id, r in responses.items():
# 		cat = [qr['options'] for qr in r if qr['question_id']==categorizeBy]
# 		if len(cat)==1:
# 			cat=cats.index(cat[0][0])
# 		else: cat = None
# 		m = members[id]
# 		telephone = [qr['response'] for qr in r if qr['question_id']==2579]
# 		assert(len(telephone)==1)
# 		telephone=telephone[0]
# 		email = 'no email'
# 		if m:
# 			email = m['email']
# 		if cat in [0,1]:
# 			f.write(str(cat)+'; '+email+'; '+name(m)+'; '+telephone+'\n')


print('Survey results for: {}'.format(survey['title']))
print('{} submissions'.format(len(submissions)))

lineWidth=.75
font=10

params = {'backend': 'ps',
          'axes.labelsize': font,
          'font.size': font,
          'legend.fontsize': font,
          'xtick.labelsize': font,
          'ytick.labelsize': font,
          'text.usetex': True,
          'lines.linewidth':lineWidth,
          #'legend.linewidth':0.5,
          'axes.linewidth':lineWidth,
          'grid.linewidth':.5,
          'patch.linewidth':lineWidth
          }

matplotlib.rcParams.update(params)

ts = [parseDate(s['submitted']) for s in submissions]

xs = matplotlib.dates.date2num(ts)
hfmt = matplotlib.dates.DateFormatter('%d/%m')

fig = plt.figure(figsize=(6,3))
plt.title(survey['title'])
ax = plt.gca()
ax.xaxis.set_major_formatter(hfmt)
plt.xlabel('Datum')
plt.ylabel('Antal svar')
plt.grid()
plt.hist(xs, bins=100)
plt.savefig(histogramFilename, bbox_inches='tight')

geometry_options = {'tmargin': '3cm', 'lmargin': '3cm'}

doc = Document(geometry_options=geometry_options)
doc.preamble.append(Command('title', ('Anonymiserad rapport om: ' if anonymize else 'Personuppgiftsinnehållande rapport om: ')+survey['title']))
doc.preamble.append(Command('author', author))
doc.preamble.append(Command('date', NoEscape(r'\today')))
doc.append(NoEscape(r'\maketitle'))
doc.append(NoEscape(r'\tableofcontents'))

doc.packages.append(Package('enumitem'))
doc.packages.append(Package('hyperref'))

nonEmpty = lambda s: not (s.isspace() or len(s)==0)

with doc.create(Section('Svarsfrekvens')):
	doc.append('{} personer har svarat på enkäten varav {} var anonyma.'.format(len(submissions), sum([1 for s in submissions if s['respondent']==None])))
	doc.append(NoEscape(r'\\Figure \ref{fig:hist} visar när de olika svaren kom in och kan användas för att se effekten av mailutskick och påminnelser i sociala media.'))
	with doc.create(Figure(position='h!')) as fig:
		fig.add_image(histogramFilename)
		fig.add_caption(NoEscape(r'\label{fig:hist} Histogram av enkätsvar över tid.'))

with doc.create(Section('Frågor')):
	if categorizeBy:
		q = [e for e in survey['elements'] if e['id']==categorizeBy][0]['question']
		doc.append('Medlemmar kategoriserade på vad de svarade på frågan "'+q['question']+'"\n')
		for cat, ms in catMembers.items():
			if not cat==None:
				emails=''
				for m in ms:
					if members[m]:
						emails += members[m]['email']+'; '	
				doc.append(bold(catNames[cats[cat]]))
				doc.append('\n'+emails+'\n\n')
			# cats = [o['text'] for o in q['options']]
	else:
		cats = []
	for element in survey['elements']:
		q = element['question']
		with doc.create(Subsection(q['question'] if nonEmpty(q['question']) else q['description'])):
			if nonEmpty(q['question']) and q['description']: doc.append(italic(q['description'])+NoEscape(r'\\'))

			if q['response_type'] == 'options':
				with doc.create(Center()) as centered:
					with centered.create(Tabular('l|c'+'|c'*len(cats))) as table:
						table.add_row(['Alternativ','Antal svarande']+[str(i+1) for i in range(len(cats))])
						table.add_hline()
						for o in q['options']:
							n = optionResponsesByQuestion[element['id']][o['id']]
							if categorizeBy:
								table.add_row([o['text'],str(n)]+[catOptionResponsesByQuestion[i][element['id']][o['id']] for i in range(len(cats))])
							else:
								table.add_row([o['text'],str(n),'{:.1f}%'.format(100*n/len(submissions))])
			elif q['response_type'] == 'text':
				if anonymize:
					doc.append(NoEscape(r'Anonymiserad rapport: inga textbaserade svar visas här.'))
				else:
					for id,r in textResponsesByQuestion[element['id']]:
						m=members[id]
						if nonEmpty(r):
							doc.append(bold(name(m)+': '))
							doc.append(r+'\n')
			else:
				print('ERROR: unknown response type')

if not anonymize:
	with doc.create(Section('Personer')):
		for s in submissions:
			m = s['respondent']
			with doc.create(Subsection(name(m))):
				if m:
					doc.append(italic('Email: '))
					doc.append(m['email'])
				for element in survey['elements']:
					q = element['question']
					for qr in responses[s['id']]:
						if qr['question_id']==element['id']:
							if 'response' in qr:
								if nonEmpty(qr['response']):
									doc.append(italic('\n'+q['question'] + '\n'))
									doc.append(qr['response'] + '\n')
							else:
								text = ''
								for o in q['options']:
									for ro in qr['options']:
										if ro==o['id']:
											text += o['text'] + ', '
								if len(text) > 0:
									doc.append(italic('\n'+q['question'] + '\n'))
									doc.append(text[:-2])

doc.generate_pdf('anonymizedSurveyResults' if anonymize else 'surveyResults', clean_tex=False)
