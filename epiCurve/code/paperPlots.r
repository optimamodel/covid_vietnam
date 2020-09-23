library(ggplot2)
library(plyr)
library(tools)
library(data.table)
#library(EpiEstim)
library(scales)

cat(date(),'\n')
rm(list=ls())

## plotting constants
theme_set(theme_bw(16))
fwide=15	
fhigh=10
f2wide=12	
f2high=12
psize=5
tcol='black'
mycols=scale_fill_manual(values=c("grey30","darkgoldenrod2","darkcyan"))
yname=ylab("New Confirmed Cases")
dates=scale_x_date(date_breaks ="week",labels = date_format("%d-%b"),expand=c(0.005,10))
dates2=theme(axis.text.x = element_text(angle = 90, vjust = 0.5, hjust=1))
overall=theme(panel.grid.major = element_blank(),panel.grid.minor = element_blank(),legend.position = c(0.95,0.96))
blank=guides(fill=guide_legend(title=NULL),color=FALSE)

## Plotting utilities

milearrow<-function(dat,grace=-0.,col1='grey60') 
{
require(ggplot2)
geom_curve(data=dat,aes( x = x1, y=y1, xend = date, yend = y2), curvature=grace, color = col1, arrow = arrow(length = unit(2, "mm"))) 
}
miletext<-function(dat,psize=4,colr='black') 
{
require(ggplot2)
geom_text(data=dat,aes( x = x0, y = y0, label = milestone), col=colr,hjust = 0.5, size=psize) 
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

##### Milestone data prep

# Current region name conventions:
setnames(miles,'Level','Region')
miles[,Region:=gsub('North','Northern',Region)]
miles[,Region:=gsub('South','Southern',Region)]

miles[,date:=as.Date(date,'%m/%d/%Y')]
miles[,x0:=date]
miles[,x1:=date]

miles[,y0:=40]
miles[,y1:=35]
miles[,y2:=10]


################################################# Plotting
# Epi curve dataset format
vietnamEpi=quang[Region!='Highland',list(newcases=.N),keyby=.(dxdate,Region,domestic)]



p1<-ggplot(vietnamEpi,aes(x=dxdate,y=newcases))+ geom_col(aes(fill=factor(domestic,labels=c('Imported','Domestic')))) +mycols+yname+dates+dates2+xlab('')+overall+blank+facet_grid(relevel(factor(Region),'Northern')~.) +milearrow(miles[Region!='National',])+miletext(miles[Region!='National',])+scale_color_manual(values=c('red','black'))

ggsave(p1,file='../output/paperPlot1.png',height=fhigh,width=fwide)











	



save.image('../output/paperPlots.RData')


