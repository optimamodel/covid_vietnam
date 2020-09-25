library(ggplot2)
library(plyr)
library(tools)
library(cowplot)
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
linelength=32
lheight=0.7
tcol='black'
mycols=scale_fill_manual(values=c("grey30","darkgoldenrod2","darkcyan"))
yname=ylab("New Confirmed Cases")
dates=function(dat) scale_x_date(date_breaks ="week",limits=range(dat$date),breaks=seq(as.Date('2020-1-6'),as.Date('2020-9-21'),7),labels = date_format("%d-%b"),expand=c(0.1,0.1))
dates2=theme(axis.text.x = element_text(angle = 90, vjust = 0.5, hjust=1))
overall=theme(panel.grid.major = element_blank(),panel.grid.minor = element_blank(),legend.position = c(0.93,0.25),legend.background = element_rect(linetype=1))
blank=guides(fill=guide_legend(title=NULL),color=FALSE)
textcol=scale_color_manual(values=c('black','red','blue'))

## Plotting utilities

milearrow<-function(dat,grace=-0.,col1='grey60',...) 
{
require(ggplot2)
geom_curve(data=dat,aes( x = x1, y=y1, xend = date, yend = y2,color=factor(colcode)), curvature=grace, arrow = arrow(length = unit(2, "mm")),alpha=0.8,...) 
}
miletext<-function(dat,psize=4,colr='black',...) 
{
require(ggplot2)
geom_label(data=dat,aes( x = x0, y = y0, label = milestone,color=factor(colcode)), lineheight = lheight, size=psize,hjust = 0.5,vjust=0.5,...) 
}
  

################################################################# Read

quang=fread('../data/Case and close contact list_Updates_22Sep2020.csv',skip=6)
provinces=fread('../data/vietProvinces.csv')
miles=fread('../data/Milestones_updates_Revised_4.csv')

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

########################################## Milestone label prep

miles[,date:=as.Date(date,'%m/%d/%Y')]
setkey(miles,date)

# Current region name conventions:
setnames(miles,'Level','Region')
miles[,Region:=gsub('North','Northern',Region)]
miles[,Region:=gsub('South','Southern',Region)]

# errata
miles[,milestone:=gsub('dearpart','depart',milestone)]
miles[,milestone:=gsub('Contract','Contact',milestone)]
miles[,milestone:=gsub('Commuity','Community',milestone)]
miles[,milestone:=gsub('detected Hai','detected in Hai',milestone)]
miles[,milestone:=gsub('Flights ban','Flight ban',milestone)]
miles[,milestone:=gsub('A city','Danang city',milestone)]
miles[milestone=='Ban on public gatherings',milestone:=paste(milestone,'in Danang')]
miles[milestone=='Lockdown relaxed',milestone:=paste('Danang',tolower(milestone))]
miles[milestone=='Lockdown 3 hospitals with case detection and surrounding house blocks',
	milestone:='Lockdown 3 hospitals and surrounding house blocks, with case detection']
##################### X coordinate
miles[,x0:=date]


### Danang, shifting x coords around wave
miles[grep('99',milestone),x0:=x0-50]
miles[milestone=='Ban on public gatherings in Danang',x0:=x0-30]
miles[grep('Community active',milestone),x0:=x0+30]
miles[grep('Lockdown 3',milestone),x0:=x0-50]
miles[grep('city lockdown',milestone),x0:=x0-14]
#miles[grep('99',milestone),x0:=x0-50]

# One in Northern
miles[grep('Vinh Phuc',milestone),x0:=x0-15]


# Edge effects?
#miles[date<as.Date('2020-2-1'),x0:=x0+7]
#miles[date>as.Date('2020-9-10'),x0:=x0-7]
miles[grep('north of Hanoi',milestone),x0:=x0-10]

miles[grep('Targeted lockdown',milestone),x0:=x0+7]
miles[grep('Lockdown',milestone),x0:=x0+14]

### Arrow origin's x coordinate
miles[,x1:=x0]
# And... Danang, where else
miles[grep('Community active',milestone),x1:=x1-28]
miles[grep('city lockdown',milestone),x1:=x1+12]

############# Y coordinate, generating "ladder"

miles[,y0:=rep(seq(55,25,-10),1+.N/4)[1:.N],by='Region']
miles[Region=='National',y0:=rep(seq(40,16,-4),1+.N/7)[1:.N]]

### Danang, shifting y coords around wave
miles[Region=='Central' & date>as.Date('2020-7-1'),y0:=y0+10]
miles[grep('99',milestone),y0:=y0-20]
miles[milestone=='Ban on public gatherings in Danang',y0:=y0+10]
miles[grep('Danang citywide',milestone),y0:=y0-10]
miles[grep('Community active',milestone),y0:=y0+10]
miles[grep('One person',milestone),y0:=y0+5]
miles[milestone=='Danang lockdown relaxed',y0:=20]

### Adjusting y for isolated milestones (so they're not "hanging high")

miles[,dist1:=c(linelength,diff(x0)),by='Region']
miles[,dist2:=c(diff(x0),linelength),by='Region']
miles[Region=='National' & pmin(dist1,dist2)>=linelength,y0:=40]
miles[Region!='National' & pmin(dist1,dist2)>=linelength,y0:=35]


miles[,y1:=y0-5]
miles[y1<5,y1:=5]
#miles[,y2:=y0-20]
# Calibrating arrowheads to case counts...
episums=vietnamEpi[,list(allcases=sum(newcases)),keyby=.(dxdate,Region)]
miles[,cases:=episums$allcases[match(paste(date,Region),paste(episums$dxdate,episums$Region))]]
miles[is.na(cases),cases:=0]
miles[,y2:=cases+2]

# line breaks
miles[nchar(milestone)>linelength,milestone:=gsub(paste('(.{',linelength,'})(\\s)',sep=''), '\\1\n',milestone)]

# differential color for lockdown and reopening?
miles[,colcode:=1]
miles[grep('[Ll]ockdown',milestone),colcode:=2]
miles[grep('[Rr]elax',milestone),colcode:=3]
miles[grep('[Rr]eopen',milestone),colcode:=3]


miles[Region=='National' & colcode>1,y0:=50]
miles[Region=='National' & grepl('Rural',milestone),y0:=45]
#miles[Region=='National' & colcode==3,y0:=45]
miles[Region=='National',y1:=y0+2]
miles[Region=='National',y2:=60]


################################################# Plotting

p1<-ggplot(vietnamEpi,aes(x=dxdate,y=newcases))+ geom_col(width=1,aes(fill=factor(domestic,labels=c('Imported','Domestic')))) +mycols+yname+dates(miles)+dates2+xlab('')+overall+blank+facet_grid(relevel(factor(Region),'Northern')~.) +milearrow(miles[Region!='National',])+miletext(miles[Region!='National',])+textcol+theme(plot.margin=unit(c(.002,.002,-0.03,.002),"npc"))



p2<-ggplot(miles[Region=='National',],aes(label=milestone,x=date,y=y0,color=factor(colcode)))+ milearrow(miles[Region=='National',])+geom_label(hjust=0.5,vjust=0.5,size=3.,lineheight=lheight)  + dates(miles)+dates2+textcol+blank+scale_y_continuous(limits=c(12,60),expand=c(0,0))+theme_void()+theme(plot.margin=unit(c(0,.2,.2,0.2),"cm"))
#plot.background = element_rect(fill = "grey90"))

ggsave(plot_grid(p1,p2,rel_heights=c(3.5,1),align='v',axis='rl',ncol=1),file='../output/paperPlot1.png',height=13,width=15)
#ggsave(ggarrange(p1,p2,heights=c(3.5,1),padding=0,align='v'),file='../output/paperPlot1.png',height=13,width=15)


cat(date(),'\n')



save.image('../output/paperPlots.RData')


