import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import os
import seaborn as sns
import requests
from bs4 import BeautifulSoup
import folium
import json
import branca.colormap as cm
from ipywidgets import interact, interactive, fixed, interact_manual

''' N.B: PatentsView.org API does not allow us to get more than 100'000 per request.
    In case there is more than 100'000 patents, we will divide our request into 2 chunks, namely 2 times 6 months,
    if we were to collect patents for a given year. '''

def BASE_URL():
    ''' Returns the base URL of PatentsView website '''
    return 'http://www.patentsview.org/api/patents/query?'

def get_nb_patents_month(month, year):
    ''' Returns the number of patents for a given month of a given year '''
    s = ''

    #Special case: if (month == December) we take the patents from December 1st to to January 1st of the following year
    if(month!='12'):
        s = year+'-'+str(int(month)+1)
    else:
        s = str(int(year)+1)+'-01'
    #query to be sent
    query = 'q={"_and":[{"_gte":{"patent_date":"'+year+'-'+month+'-01"}},\
        {"_lt":{"patent_date":"'+ s +'-01"}}]}'

    #Sends a GET request and store the data in a JSON file
    r = requests.get(BASE_URL()+query).json()
    #Check if the number of patents obtained is larger than 100'000, which leads to biased result
    if pd.DataFrame(r).total_patent_count[0] > 100000:
        print("Number of patents exceeds 100'000, please take a shorter interval")
    #The total number of patents is contained in every rows of the dataframe (take 0 by default)
    return pd.DataFrame(r).total_patent_count[0]


def get_nb_patents_year(year):
    ''' Returns the number of granted patent for a given year (12 months). Uses get_nb_patents_month() to
    add every months together'''
    nb_patent=0
    for i in range(12):
        #Special case, if the month number is less than 10, append a '0'
        if i<10:
            nb_patent+=get_nb_patents_month('0'+str(i), year)
        else:
            nb_patent+=get_nb_patents_month(str(i), year)
    return nb_patent



def get_nb_patent_country(country):
    ''' Requests all the patents of the year 2016 for a given country '''
    ''' Outputs the inventor country for checking purposes '''
    query='q={"_and":[{"_gte":{"patent_date":"1996-01-01"}},\
    {"_lt":{"patent_date":"2018-01-01"}},{"_eq":{"inventor_country":"'+country+'"}}]}'
    output='&f=["inventor_country"]'
    r = requests.get(BASE_URL()+query+output).json()

    #Catch an exception in case a given country did not deliver any patent in 2016, i.e. is not cited in the DataBase
    try:
        nb_patents= pd.DataFrame(r).total_patent_count[0]
        #Special case: The request cannot give more than 100'000 patents, we break the time interval into 2
        if nb_patents >= 100000:
            #Send the request for twice 6 month (result always less than 100000)
            query='q={"_and":[{"_gte":{"patent_date":"2016-01-01"}},{"_lt":{"patent_date":"2016-07-01"}},{"_eq":{"inventor_country":"'+country+'"}}]}'
            r = requests.get(BASE_URL()+query+output).json()
            #number of patent is countained in every rows of the dataframe
            nb_patents= pd.DataFrame(r).total_patent_count[0]
            query='q={"_and":[{"_gte":{"patent_date":"2016-07-01"}},{"_lt":{"patent_date":"2017-01-01"}},{"_eq":{"inventor_country":"'+country+'"}}]}'
            r = requests.get(BASE_URL()+query+output).json()
            #Add the 2 requests together
            nb_patents += pd.DataFrame(r).total_patent_count[0]
    except ValueError: #In case no patents are found
        nb_patents=0
    return int(nb_patents)



def ret_color(feature, colors):
    ''' Maps each country (precisely its ISO-ALPHA 2 code) to a color depending on the number of patents'''
    if (feature['properties']['iso_a2'] in colors.keys()):
        return colors[feature['properties']['iso_a2']]
    else:
        #Returns the white color if a country does not show up in the list of patents
        return '#ffffff'

def get_patents(year_start, month_start, year_end, month_end):
    '''Returns the granted patents between the given dates (year and month)'''
    '''Get patent_id, patent_number and patent_title for granted patents between given dates.'''

    query='q={"_and":[{"_gte":{"patent_date":"%d-%d-01"}},\
                      {"_lt":{"patent_date":"%d-%d-01"}}]}\
                      &o={"page":1,"per_page":100}' % (year_start, month_start, year_end, month_end)
    return requests.get(BASE_URL() + query).json()



def get_company(year_start, month_start, year_end, month_end ,total_page_num=10):
    ''' Get all the granted patents by companies, between the two given dates'''
    company_total_patent = dict()
    for page_num in range(total_page_num):
        patent_json = get_patents_company(2017, 1, 2017, 5, page_num+1)
        if pd.DataFrame(patent_json).total_patent_count[0] > 100000:
            print("Number of patents exceeds 100'000, please take a shorter interval")
        for patent in patent_json['patents']:
            company_name = patent['assignees'][0]['assignee_organization']
            total_patent =  patent['assignees'][0]['assignee_total_num_patents']
            company_total_patent[company_name] = total_patent
    return company_total_patent



def get_patents_company(year_start, month_start, year_end, month_end, page_num):
    '''Get all granted patents by assignee_organization (company name) and assignee_total_num_patents (number of that companie's patents)
        between given dates.'''
    query='q={"_and":[{"_gte":{"patent_date":"%d-%d-01"}},\
                      {"_lt":{"patent_date":"%d-%d-01"}}]}\
                      &o={"page":%d,"per_page":10000}\
                      &f=["assignee_organization", "assignee_total_num_patents"]'\
                      % (year_start, month_start, year_end, month_end, page_num)
    return requests.get(BASE_URL() + query).json()


# Helper function
def get_patents_country_sector(year_start, month_start, year_end, month_end, page_num):
    '''Get all granted patents by assignee_organization (company name) and assignee_total_num_patents (number of that companie's patents)
        by sector, using CPC between given dates. (CPC stands for Cooperative Patent Classification)'''
    query='q={"_and":[{"_gte":{"patent_date":"%d-%d-01"}},\
                      {"_lt":{"patent_date":"%d-%d-01"}}]}\
                      &o={"page":%d,"per_page":10000}\
                      &f=["assignee_country", "cpc_group_id"]'\
                      % (year_start, month_start, year_end, month_end, page_num)
    return requests.get(BASE_URL() + query).json()




def get_countries_by_sectors():
    ''' Returns a dictionary that contains categorized patents into sectors,
     for each country, using CPC (Cooperative Patent Classification)'''
    country_total_patent_category = dict()
    total_page_num = 3
    for i in range(11):
        for page_num in range(total_page_num):
            patent_json = get_patents_country_sector(2016, i+1, 2016, i+2, page_num+1)
            if patent_json['patents'] != None:
                for patent in patent_json['patents']:
                    country = patent['assignees'][0]['assignee_country']
                    patent_categories = patent['cpcs']
                    for category in patent_categories:
                        if country and category['cpc_group_id']:
                            code = category['cpc_group_id'][0]
                            if country in country_total_patent_category:
                                if code in country_total_patent_category[country]:
                                    country_total_patent_category[country][code] += 1
                                else:
                                    country_total_patent_category[country][code] = 1
                            else:
                                country_total_patent_category[country] = dict()
                                country_total_patent_category[country][code] = 1
    return country_total_patent_category



def fıgure_by_sector(category, label, fig_index, axes, df):
    ''' Plots the TOP10 countries for a given sector (Categories 'A','B','C', etc.), in terms of the number of granted patents'''
    a = df.sort_values(by=category, ascending=False)
    a.head(10).plot.bar(y=category, figsize=(9,7), fontsize=20, subplots=True, ax=axes[fig_index[0], fig_index[1]], label=label)

category_label = [('A', 'Human Necessities'),('B', 'Operations and Transport'),('C', 'Chemistry and Metallurgys'),('D', 'Textiles'),\
                  ('E', 'Fixed Constructions'),('F', 'Mechanical Engineering'),('G', 'Physics'),('H', 'Electricity'),\
                  ('Y', 'Emerging Cross-Sectional Technologies'),]



def spider_chart(df, index, title=''):
    ''' Draws a spider chart showing the involvment level of a given country in all the 7 sectors in CPC
        (Cooperative Patent Classification) by showing the relative number of granted patents for each sector, country-wise'''
    labels = np.array(['A', 'B', 'C', 'D', 'E', 'F', 'G', 'H', 'Y'])

    stats = df.loc[index, labels].values
    angles=np.linspace(0, 2*np.pi, len(labels), endpoint=False)

    stats=np.concatenate((stats,[stats[0]]))
    angles=np.concatenate((angles,[angles[0]]))

    fig= plt.figure()
    ax = fig.add_subplot(111, polar=True)   # Setting up a polar axis
    ax.plot(angles, stats, 'o-', linewidth=1.5, color='r')  # Draw the plot (or the frame on the radar chart)
    ax.fill(angles, stats, alpha=0.25, color='r') # Fills in the inner area of the spider chart

    labels_ = np.array(['Human Necessities', 'Transport', 'Chemistry',\
                       'Textiles', 'Constructions', 'MechEng',\
                       'Physics', 'Electricity', 'Cross-Sectional Technologies'])

    ax.set_title(title) # The title corresponds to the name of the given country
    ax.set_thetagrids(angles * 180/np.pi, labels_)  #Label the axis using shorter terms


def query_ipc_by(field, flag):
    query = '{"_or":['
    for i,val in enumerate(field):
        query += '{"_eq":{' + flag + ':"'+ val +'"}}'
        if i != len(field) - 1:
            query += ','
    query += ']}'
    return query

#Get patents by IPC, and then filter them by keywords
#A typical IPC symbol is H01L 31, H=section 01=classification 31=group
#Look at http://www.wipo.int/classifications/ipc/en/ to find the IPC symbols of a category#                                                                     (used for FinTech)
def get_patents_keywords_ipc(keywords, year, list_ipc):
    ''' Returns all the patents containing the given keywords, for a given year'''

    #Year query parameters
    query_year = '{"_gte":{"patent_date":"'+year+'-01-01"}},{"_lt":{"patent_date":"'+str(int(year)+1)+'-01-01"}}'

    nb_patents=0
    dfPatents=pd.DataFrame()
    #Send a query for every keyword
    for (section, classification, group) in list_ipc:
        query_group = '{"_eq":{"ipc_main_group":"'+group+'"}}'
        query_section = '{"_eq":{"ipc_section":"'+section+'"}}'
        query_classification = '{"_eq":{"ipc_class":"'+classification+'"}}'

        query='q={"_and":['+query_year+','+query_section+','+query_classification+','+query_group+']}'
        output='&f=["patent_title","patent_number","ipc_section","ipc_main_group","ipc_class","patent_num_cited_by_us_patents",\
                      "assignee_country", "assignee_organization", "patent_date",\
                      "inventor_first_name", "inventor_last_name", "inventor_id"]'


        option='&o={"per_page":10000}'
        #Exception handler in case no patent is found for a given keyword
        try:
            r = requests.get(BASE_URL()+query+output+option).json()
            nb_patents+=pd.DataFrame(r).total_patent_count[0]
            dfPatents=pd.concat([dfPatents,pd.DataFrame(r)],ignore_index=True)
        except ValueError:
            pass

    #Clean the dataframe
    dfPatents.reindex(list(range(len(dfPatents))))

    columns = ["patent_title","patent_number", "IPCs", "patent_num_cited_by_us_patents","assignees",\
               "patent_date", "inventors"]

    dfPatents_cleaned=pd.DataFrame(columns=columns)
    for col in columns:
        dfPatents_cleaned[col]=list(map(lambda x: x[col], dfPatents.patents))


    filter_list=[]
    keyWordFound=False
    for title in dfPatents_cleaned.patent_title:
        for tuple_keyword in keywords:
            for i in range(len(tuple_keyword)):
                if tuple_keyword[i] not in title:
                    keyWordFound=False
                    break
                if i == len(tuple_keyword)-1:
                    keyWordFound=True
            if keyWordFound==True:
                break
        filter_list.append(keyWordFound)

    dfPatents_cleaned = dfPatents_cleaned.loc[filter_list]
    return dfPatents_cleaned, len(dfPatents_cleaned)


#A typical IPC symbol is H01L 31, H=section 01=classification 31=group
#Look at http://www.wipo.int/classifications/ipc/en/ to find the IPC symbols of a category
def get_nb_patent_years_keyword(years,keywords,list_ipc):
    list_patent_nb = []
    df = pd.DataFrame()
    for i in years:
        if (i != 2005):
            dfPatent, nb_patent = get_patents_keywords_ipc(keywords,str(i),list_ipc)
            list_patent_nb.append(nb_patent)
            df= pd.concat([df,dfPatent],ignore_index=True)
    return list_patent_nb, df

#plot the number of patents
#Parameters: x,y = data
#           x_axis, y_axis = labels of axes
#           title
def plt_nb_patent(x,y,x_axis,y_axis,title):
    plt.plot(x,y)
    plt.xlabel(x_axis)
    plt.ylabel(y_axis)
    plt.title(title)
    plt.grid(True, 'major', 'y', ls='--', lw=.5, c='k', alpha=.3)


#Save df to excel wile with the filename excel_title
def savedfexcel(df, excel_title):
    writer = pd.ExcelWriter('{0}.xlsx'.format(excel_title))
    df.to_excel(writer,'Sheet1')
    writer.save()

#Get the growth in nb of patents according to the number of patents and the year
def get_growth(years, list_nb_patents):
    growth=[]
    for i in range(len(years)-1):
        growth+=[(list_nb_patents[i+1]-list_nb_patents[i])/list_nb_patents[i]*100]
    return growth



#The function build_dataframe research all these data by using the API of patentsview
def build_dataframe(years,keywords,list_ipc):
    list_patent_nb=[]
    dfPatents=pd.DataFrame()
    for i in years:
        [dfPatentsYear, nb_patent]=get_patents_keywords_energy(keywords,str(i),list_ipc)
        dfPatentsYear['year']=i
        dfPatents=pd.concat([dfPatentsYear,dfPatents],ignore_index=True)
        dfPatents.set_index([list(range(len(dfPatents)))],inplace=True)
    return dfPatents

#df_get_nb_by_group_and_clean function take in paramenter a dataframe with all the patents and a column for the year, country and company.
#The second parameter is 'inventor_country' or 'assignee_organisation' depending if we want to classify by country
#or companies. The last paramenter is True if we want to include a column 'total' which is the sum of umber of
#patents for a company or country for every year. The function returns the companies or countries classified
#from the biggest to the smallest patent provider. Each colums contains the number of patents for each years.
#This function will be used many times below to classify the number of patents by country or companies.
def df_get_nb_by_group_and_clean(df, group, years, showtotal=False):
    dfcopy=df.copy()
    dfcopy['nb patent']=1
    dfpatentgroup = dfcopy.groupby(['year',group]).sum() #group by countries or companies
    dfpatentgroup=dfpatentgroup.unstack(level=1).fillna(0) #unstack the years
    dfpatentgroup.sort_values(by=years,axis=1, ascending=False,inplace=True) #sort by nb of patents
    dfpatentgroup_copy=dfpatentgroup.transpose().copy() #transpose the dataframe
    dfpatentgroup_copy['total'] = dfpatentgroup_copy.apply(sum, axis=1) #add a new column total
    dfpatentgroup_copy.reset_index(inplace=True) #Reset the index
    dfpatentgroup_copy.drop('level_0', axis=1, inplace=True)
    dfpatentgroup_copy.set_index(group, inplace=True) #set the company or country as index

    if showtotal==False: #Keep or remove the column total after sorting by best company/country
        clean_df = dfpatentgroup_copy.sort_values(by='total', ascending=False).drop('total',axis=1)
    else:
        clean_df = dfpatentgroup_copy.sort_values(by='total', ascending=False)
    return clean_df

#Read the excel file containing a dataframe
def read_df(PATH):
    return pd.read_excel(PATH + '.xlsx')

#Plot the interactive barplot. plt_interactive_by_countryis called in the interact function
#The function interact from ipywidgets library allows to create a scroll bar and trigger different event according
#to the selection. When a sector is selected, the function plt_interactive_by_country is called. This function must
#take one parameter which is the list of the sectors. Then, according to the technology selected, the related
#barplot is displayed
def plt_interactive_by_country(sector):

    feature = 'inventor_country'
    years=list(range(2010,2017))

    if sector == 'solar photo':
        df=df_get_nb_by_group_and_clean(read_df('patent_solar_photo'), feature, years, False).head(10)
    if sector == 'solar termal':
        df=df_get_nb_by_group_and_clean(read_df('patent_solar_thermo'), feature, years, False).head(10)
    if sector == 'wind':
        df=df_get_nb_by_group_and_clean(read_df('patent_wind'), feature, years, False).head(10)
    if sector == 'hydro':
        df=df_get_nb_by_group_and_clean(read_df('patent_hydro'), feature,years, False).head(10)
    if sector == 'tidal and wave':
        df=df_get_nb_by_group_and_clean(read_df('patent_wave_tidal'), feature,years, False).head(10)
    if sector == 'carbon capture':
        df=df_get_nb_by_group_and_clean(read_df('patent_carbon_storage'), feature,years, False).head(10)
    if sector == 'renewable':
        df=df_get_nb_by_group_and_clean(read_df('patent_renewable'), feature, years, False).head(10)
    df.plot.barh(stacked=True, fontsize=20, figsize=(20,13), rot=0, grid=True)
    plt.show()



#Same function as before but for the companies
def plt_interactive_by_company(sector):

    feature = 'assignee_organization'
    years=list(range(2010,2017))

    if sector == 'solar photo':
        df=df_get_nb_by_group_and_clean(read_df('patent_solar_photo'), feature, years, False).head(10)
    if sector == 'solar termal':
        df=df_get_nb_by_group_and_clean(read_df('patent_solar_thermo'),feature, years, False).head(10)
    if sector == 'wind':
        df=df_get_nb_by_group_and_clean(read_df('patent_wind'),feature, years, False).head(10)
    if sector == 'hydro':
        df=df_get_nb_by_group_and_clean(read_df('patent_hydro'), feature,years, False).head(10)
    if sector == 'tidal and wave':
        df=df_get_nb_by_group_and_clean(read_df('patent_wave_tidal'), feature,years, False).head(10)
    if sector == 'carbon capture':
        df=df_get_nb_by_group_and_clean(read_df('patent_carbon_storage'), feature,years, False).head(10)
    if sector == 'renewable':
        df=df_get_nb_by_group_and_clean(read_df('patent_renewable'), feature, years, False).head(10)
    df.plot.barh(stacked=True, fontsize=20, figsize=(20,13), rot=0, grid=True)
    plt.show()

#This function plot all the plots of number of patents for the energy sectors, classified by
#countries or companiy. Feature = 'inventor_country' or 'assignee_organisation'
def plot_by_country(feature):
    years=list(range(2010,2017))
    fig=plt.figure()
    ax=fig.add_subplot(421)
    df=df_get_nb_by_group_and_clean(read_df('patent_solar_photo'), feature, years, False).head(10)
    df.plot.barh(stacked=True, fontsize=15, figsize=(20,13), rot=0, grid=True,ax=ax)
    plt.title('solar photo', fontsize=15)
    ax1=fig.add_subplot(422)
    df=df_get_nb_by_group_and_clean(read_df('patent_solar_thermo'), feature, years, False).head(10)
    df.plot.barh(stacked=True, fontsize=15, figsize=(20,13), rot=0, grid=True,ax=ax1)
    plt.title('solar thermal', fontsize=15)
    ax2=fig.add_subplot(423)
    df=df_get_nb_by_group_and_clean(read_df('patent_wind'), feature, years, False).head(10)
    df.plot.barh(stacked=True, fontsize=15, figsize=(20,13), rot=0, grid=True,ax=ax2)
    plt.title('wind', fontsize=15)
    ax3=fig.add_subplot(424)
    df=df_get_nb_by_group_and_clean(read_df('patent_hydro'), feature, years, False).head(10)
    df.plot.barh(stacked=True, fontsize=15, figsize=(20,13), rot=0, grid=True,ax=ax3)
    plt.title('hydro', fontsize=15)
    ax4=fig.add_subplot(425)
    df=df_get_nb_by_group_and_clean(read_df('patent_wave_tidal'), feature, years, False).head(10)
    df.plot.barh(stacked=True, fontsize=15, figsize=(20,13), rot=0, grid=True,ax=ax4)
    plt.title('wave and tidal', fontsize=15)
    ax5=fig.add_subplot(426)
    df=df_get_nb_by_group_and_clean(read_df('patent_carbon_storage'), feature, years, False).head(10)
    df.plot.barh(stacked=True, fontsize=15, figsize=(20,13), rot=0, grid=True,ax=ax5)
    plt.title('carbon capture and storage', fontsize=15)
    ax6=fig.add_subplot(427)
    df=df_get_nb_by_group_and_clean(read_df('patent_renewable'), feature, years, False).head(10)
    df.plot.barh(stacked=True, fontsize=15, figsize=(20,13), rot=0, grid=True,ax=ax6)
    plt.title('renewable', fontsize=15)
    if feature == 'assignee_organization':
        plt.subplots_adjust(hspace=.5, wspace=1.0)
    else:
        plt.subplots_adjust(hspace=.5)
    plt.show()

#get_patents_keywords_energy function send a request to the database for every
#ipc in the list and get all the patents back. The the patents are filtered by the keywords contained
#in the list. Ex : keywords_solar_power= [["solar", "cell"], ["solarcell"],] will keep as match every title
#that contains ("solar" and "cell") or "solarcell"
def get_patents_keywords_energy(keywords,year, list_ipc):
    ''' Returns all the patents containing the given keywords, for a given year'''

    #Year query parameters
    query_year = '{"_gte":{"patent_date":"'+year+'-01-01"}},{"_lt":{"patent_date":"'+str(int(year)+1)+'-01-01"}}'

    nb_patents=0
    dfPatents=pd.DataFrame()
    #Send a query for every keyword
    for (section, classification, group) in list_ipc:
        query_group = '{"_eq":{"ipc_main_group":"'+group+'"}}'
        query_section = '{"_eq":{"ipc_section":"'+section+'"}}'
        query_classification = '{"_eq":{"ipc_class":"'+classification+'"}}'

        query='q={"_and":['+query_year+','+query_section+','+query_classification+','+query_group+']}'
        output='&f=["patent_title","inventor_country","assignee_organization","patent_number"]'
        option='&o={"per_page":10000}'
        #Exception handler in case no patent is found for a given keyword
        try:
            r = requests.get(BASE_URL()+query+output+option).json()
            nb_patents+=pd.DataFrame(r).total_patent_count[0]
            if nb_patents > 10000:
                print('nb of patents too big (>10000)')
            dfPatents=pd.concat([dfPatents,pd.DataFrame(r)],ignore_index=True)
        except ValueError:
            pass

    #Clean the dataframe
    dfPatents.reindex(list(range(len(dfPatents))))

    columns = ["patent_title","patent_number","inventor_country","assignee_organization"]
    dfPatents_cleaned=pd.DataFrame(columns=columns)

    #Retreive the information received by the request to put it in a clean dataframe
    for col in columns:
        if col == 'inventor_country':
            dfPatents_cleaned[col]=list(map(lambda x: x['inventors'][0][col], dfPatents.patents))
        elif col == 'assignee_organization':
            dfPatents_cleaned[col]=list(map(lambda x: x['assignees'][0][col], dfPatents.patents))
        else:
            dfPatents_cleaned[col]=list(map(lambda x: x[col], dfPatents.patents))

    #Filter the dataframe by keywords
    filter_list=[]
    keyWordFound=False
    for title in dfPatents_cleaned.patent_title:
        for tuple_keyword in keywords:
            for i in range(len(tuple_keyword)):
                if tuple_keyword[i] not in title:
                    keyWordFound=False
                    break
                if i == len(tuple_keyword)-1:
                    keyWordFound=True
            if keyWordFound==True:
                break
        filter_list+=[keyWordFound]

    dfPatents_cleaned = dfPatents_cleaned.loc[filter_list]
    return [dfPatents_cleaned, len(dfPatents_cleaned)]

#get_nb_patent_years_keyword_energy retrun a list of number of patents for every years
#and by sector. This funcion uses get_patents_keywords_energy above
def get_nb_patent_years_keyword_energy(years,keywords,list_ipc):
    list_patent_nb=[]
    for i in years:
        [dfPatent, nb_patent]=get_patents_keywords_energy(keywords,str(i),list_ipc)
        list_patent_nb+=[nb_patent]
    return list_patent_nb

def get_patents_by_keywords(keywords_group,ipc_list,year,month):
    """
    Return Dataframe consists of patents whose title
    contains at least one of keywords,
    for specified ipc categories,
    on the given year.
    """

    if month == '12':
        next_month = str(int(year)+1)+'-01'
    else:
        next_month = year+'-'+str(int(month)+1)

    query_year = '{"_gte":{"patent_date":"'+year+'-'+month+'-01"}},\
                   {"_lt":{"patent_date":"'+next_month+'-01"}}'

    num_patents = 0
    patents_df = pd.DataFrame()
    for (section, classification, group) in ipc_list:

        query_section = '{"_eq":{"ipc_section":"'+section+'"}}'
        query_classification = '{"_eq":{"ipc_class":"'+classification+'"}}'
        query_group = '{"_eq":{"ipc_main_group":"'+group+'"}}'

        # 'q={"_and":['+query_year+','+query_section+','+query_classification+','+query_group+']}'
        query = 'q={"_and":['+query_year+','+query_section+','+query_classification+']}'

        output = '&f=["patent_title","patent_number","patent_num_cited_by_us_patents",\
                      "assignee_country", "assignee_organization", "patent_date",\
                      "inventor_first_name", "inventor_last_name", "inventor_id"]'
        option = '&o={"per_page":10000}'

        try:
            r = requests.get(BASE_URL()+query+output+option).json()
            num_patents += pd.DataFrame(r).total_patent_count[0]
            if num_patents >= 10000:
                print('Number of patents too big (>10000).')
                return(-1)
            patents_df = pd.concat([patents_df,pd.DataFrame(r)],ignore_index=True)
        except Exception as e:
            print('\nNo patent has been found.')
            return(-1)

    # Clean the Dataframe
    patents_df.reindex(list(range(len(patents_df))))
    columns = ["patent_title","patent_number","patent_num_cited_by_us_patents","assignees",\
               "patent_date", "inventors"]
    patents_df_cleaned = pd.DataFrame(columns=columns)

    for col in columns:
        patents_df_cleaned[col]=list(map(lambda x: x[col], patents_df.patents))

    filter_list = list()
    for title in patents_df_cleaned.patent_title:
        keyword_found = False
        for keyword in keywords_group:
            if keyword in title.lower():
                keyword_found = True
        filter_list += [keyword_found]

    patents_df_cleaned = patents_df_cleaned.loc[filter_list]
    print("Total Patents: %d | Related to AI: %d | Date: %s-%s."\
           %(num_patents, len(patents_df_cleaned), year, month))
    return patents_df_cleaned

def patents_for_all_years(year,month):

    if month == '12':
        next_month = str(int(year)+1)+'-01'
    else:
        next_month = year+'-'+str(int(month)+1)

    query = 'q={"_and":[{"_gte":{"patent_date":"'+year+'-'+month+'-01"}},\
                        {"_lt":{"patent_date":"'+next_month+'-01"}}]}'

    r = requests.get(BASE_URL()+query).json()

    num_patents = pd.DataFrame(r).total_patent_count[0]
    if num_patents > 100000:
        print('Number of patents too big (>10000).')

    print("Total Patents: %d | Date: %s-%s."%(num_patents, year, month))
    return num_patents


if __name__ == '__main__':
    #test
    patents = get_nb_patent_country('CU')
