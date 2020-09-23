library(ggplot2)
library(plyr)
library(tools)
library(gridExtra)
library(data.table)
#library(EpiEstim)
library(scales)

cat(date(),'\n')
rm(list=ls())

## plotting constants
theme_set(theme_bw(18))
fwide=15	
fhigh=10
f2wide=12	
f2high=12
psize=5
tcol='black'
mycols=scale_fill_manual(values=c("grey30","darkgoldenrod2","darkcyan"))
yname=ylab("New Confirmed Cases")
dates=scale_x_date(date_breaks ="week",labels = date_format("%d-%b"),expand=c(0.057,0.075))
dates2=theme(axis.text.x = element_text(angle = 90, vjust = 0.5, hjust=1))
overall=theme(panel.grid.major = element_blank(),panel.grid.minor = element_blank(),legend.position = c(0.93,0.94))
blank=guides(fill=guide_legend(title=NULL),color=FALSE)
textcol=scale_color_manual(values=c('black','red','blue'))

## Plotting utilities

milearrow<-function(dat,grace=-0.,col1='grey60') 
{
require(ggplot2)
geom_curve(data=dat,aes( x = x1, y=y1, xend = date, yend = y2,color=factor(colcode)), curvature=grace, arrow = arrow(length = unit(2, "mm"))) 
}
miletext<-function(dat,psize=4.5,colr='black') 
{
require(ggplot2)
geom_text(data=dat,aes( x = x0, y = y0, label = milestone,color=factor(colcode)), lineheight = 0.8, size=psize,hjust = 0.5,vjust=0.5) 
}
  

###################################################### Read

quang=fread('../data/Case and close contact list_Updates_22Sep2020.csv',skip=6)
provinces=fread('../data/vietProvinces.csv')
miles=fread('../data/Milestones_updates_Revised_3.csv')

#quang[,CaseID:=as.integer(gsub('NB','',CaseID))]

## Imported vs. Domestic, cognizant of typos ;)
quang[,domestic:=grepl('D',Case_cat)]

#quang[,Gender:=tolower(Gender)]
#setkey(quang,CaseID)

#### Regions!
provinces[,Province:=toTitleCase(Province)]
quang[,Province:=toTitleCase(Province)]
quang[,Region:=provinces$Region[match(Province,provinces$Province)]]

# Errata etc.
quang[Province %in% c('Hanoi','Bac Can'),Region:='North']
quang[Province %in% c('TPHCM','BR-VT'),Region:='South']
quang[Province %in% c('Da Nang','Quang Tri'),Region:='Central']
quang[Province %in% c('Daklak'),Region:='Highland']

# Current region name conventions:
quang[,Region:=gsub('North','Northern',Region)]
quang[,Region:=gsub('South','Southern',Region)]

### other cleaning
# date mess (some American, some old-world)
quang[,dxdate:=as.Date(diagdate,'%m/%d/%Y')]
quang[is.na(dxdate),dxdate:=as.Date(diagdate,'%d/%m/%Y')]

#fwrite(quang,file=paste('../output/VietnamLine',dim(quang)[1],'.csv',sep=''))

# Epi curve dataset format
vietnamEpi=quang[Region!='Highland',list(newcases=.N),keyby=.(dxdate,Region,domestic)]

##### Milestone data prep

# Current region name conventions:
setnames(miles,'Level','Region')
miles[,Region:=gsub('North','Northern',Region)]
miles[,Region:=gsub('South','Southern',Region)]

miles[,date:=as.Date(date,'%m/%d/%Y')]
setkey(miles,date)
miles[,x0:=date]
# Danang
miles[grep('99',milestone),x0:=x0-50]
# Edge effects?
miles[date<as.Date('2020-2-1'),x0:=x0+7]
miles[date>as.Date('2020-9-10'),x0:=x0-7]

miles[,x1:=x0]

miles[,y0:=rep(seq(50,20,-10),.N/4)[1:.N],by='Region']
miles[Region=='National',y0:=rep(seq(40,16,-4),.N/4)[1:.N]]
# Danang outbreak
miles[Region=='Central' & date>as.Date('2020-7-1'),y0:=y0+30]
miles[grep('99',milestone),y0:=y0-20]
miles[,y1:=y0-5]
miles[y1<5,y1:=5]
#miles[,y2:=y0-20]
# Calibrating to case counts...
episums=vietnamEpi[,list(allcases=sum(newcases)),keyby=.(dxdate,Region)]
miles[,cases:=episums$allcases[match(paste(date,Region),paste(episums$dxdate,episums$Region))]]
miles[is.na(cases),cases:=0]
miles[,y2:=cases+1]

# line breaks?
miles[nchar(milestone)>40,milestone:=gsub('(.{40})(\\s)', '\\1\n',milestone)]

# differential color for lockdown?
miles[,colcode:=1]
miles[grep('lockdown',milestone),colcode:=2]
miles[grep('[Rr]elax',milestone),colcode:=3]
miles[grep('reopen',milestone),colcode:=3]

################################################# Plotting



p1<-ggplot(vietnamEpi,aes(x=dxdate,y=newcases))+ geom_col(width=1,aes(fill=factor(domestic,labels=c('Imported','Domestic')))) +mycols+yname+dates+dates2+xlab('')+overall+blank+facet_grid(relevel(factor(Region),'Northern')~.) +milearrow(miles[Region!='National',])+miletext(miles[Region!='National',])+textcol

ggsave(p1,file='../output/paperPlot1.png',height=fhigh,width=fwide)

p2<-ggplot(miles[Region=='National',],aes(label=milestone,x=date,y=y0,color=factor(colcode)))+geom_label(hjust=0.5,vjust=0.5,size=4.5,lineheight=.8)+dates+dates2+textcol+blank+theme_void()









	



save.image('../output/paperPlots.RData')


