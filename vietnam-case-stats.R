########################################
# Script for analysing Vietnam's case data
#
# Date last modified: Aug 5, 2020
# For questions on this script, contact robyn@math.ku.dk
########################################

########################################
# Load libraries
########################################
library (ggplot2)
library (readxl)
library (dplyr)
library (reshape2)
library (ggpubr)
library(lubridate)
library(tidyverse)

# Set working directory
setwd(dirname(rstudioapi::getActiveDocumentContext()$path))

########################################
# Import and clean data
########################################
rawcases <- read_excel("1_Case and close contact list_Updates_22August_v2.xlsx",  skip = 6)
rawcases$Region[rawcases$Region=="Highland"] = "Central"
rawcases$Source[rawcases$Source=="Detected case"] = "Domestic"
rawcases$Source[rawcases$Source=="Domestic case"] = "Domestic"
rawcases$Source[rawcases$Source=="Imported case"] = "Imported"
rawcases$Source = factor(rawcases$Source)
rawcases$diagdate <- ymd(rawcases$diagdate)

fontfamily="Optima"
ann_text <- data.frame(Age = rep(50,3),wt = 5,lab = "Text",
                       cyl = factor(8,levels = c("4","6","8")))

dat_text <- data.frame(
  label = c("171 domestic cases\n(86% of total)", "70 domestic cases\n(25% of total)", "29 domestic cases\n(23% of total)"),
  Source = c(NA, NA, NA),
  Region   = c("Central", "North", "South")
)

########################################
# Data visualization by source and region
########################################
# Histogram by age
(g <- ggplot(data=subset(rawcases, !is.na(Region)), aes(x=Age, fill=Source)) +
  geom_histogram() + 
  facet_wrap(~Region) + 
  theme_pubclean() + 
  theme(text=element_text(size=16,  family=fontfamily)) + 
  theme(legend.background = element_rect(fill = "white"),
        legend.key = element_rect(fill = "white", color = NA))  +
  ylab("Cases") +
  xlab("Age") +
  labs(fill = "") +    scale_fill_brewer(palette="Set2") +
  #annotate(dat_text, x=50, y=38, label=lave, hjust=0, family=fontfamily) +
  geom_text(data = dat_text, mapping = aes(x=52, y=45, label = label, family=fontfamily)) 
  )

fn <- "cases_by_age_source_region.png"
ggsave(fn, g, device="png", dpi=300)

# Time series by source
df <- data.frame(diagdate = seq(as.Date("2020/1/23"), as.Date("2020/8/2"), "days")) %>%
  left_join(rawcases  %>% group_by(Region, Source, Cluster) %>% count(diagdate)) %>%
  rename(date=diagdate,new_diagnoses=n) %>% filter(!is.na(Region) & !is.na(Source))
ggplot(df, aes(x=date, y=new_diagnoses, fill=Source)) +
    geom_bar(stat="identity") + 
    facet_wrap(~Region) + 
    theme_pubclean() + 
    theme(text=element_text(size=16,  family=fontfamily)) + 
    theme(legend.background = element_rect(fill = "white"),
          legend.key = element_rect(fill = "white", color = NA))  +
    ylab("Cases") +
    xlab("Date") +
    labs(fill = "") +
    scale_x_date(date_labels = "%b", date_breaks = "1 month") 

fn <- "cases_by_date_source_region.png"
ggsave(fn, plot = last_plot(), device="png", dpi=300)

df2 <- df  %>% group_by(Region, Source) %>% summarise(total = sum(new_diagnoses))


# Make dataframe with data from central region 
diagnoses <- data.frame(diagdate = seq(as.Date("2020/6/15"), as.Date("2020/8/22"), "days")) %>%
  left_join(rawcases %>% filter(Region=="Central", Source=="Domestic") %>% count(diagdate))  %>%
  rename(date=diagdate,new_diagnoses=n) %>% replace(is.na(.), 0)

deaths <- data.frame(Dead = seq(as.Date("2020/7/25"), as.Date("2020/8/22"), "days")) %>%
  left_join(rawcases %>% filter(Region=="Central", Source=="Domestic") %>% count(Dead))  %>%
  rename(date=Dead,new_deaths=n) %>% replace(is.na(.), 0)

## Get testing data
central_codes <- read_excel("Testing_COVID19_HK_22Aug.xlsx", skip = 2) %>%
  rename(en_name="...3" ,Region="...4" ) %>%
  filter(Region=="Central") 

tests <- data.frame(testdate = seq(as.Date("2020/6/15"), as.Date("2020/8/22"), "days"))
tests$new_tests = NA
dates <- c("15_6", "16_6", "17_6", "18_6", "19_6", "20_6", "21_6", "22_6", "23_6", "24_6", "25_6", "26_6", "27_6", "28_6", "29_6", "30_6","1_7","2_7","3_7","4_7","5_7","6_7","7_7","8_7","9_7","10_7","11_7","12_7","13_7","14_7","15_7","16_7","17_7","18_7","19_7","20_7","21_7","22_7","23_7","24_7","25_7","26_7","27_7","28_7","29_7","30_7","31_7","1_8","2_8","3_8","4_8","5_8","6_8","7_8","8_8","9_8","10_8","11_8","12_8","13_8","14_8","15_8","16_8","17_8","18_8","19_8","20_8","21_8","22_8")

#%>% replace(is.na(.), 0) %>% 
running_total = c()
for (d in dates) {
  if (d %in% c("14_7","20_7","21_7")) {todays_total <- 0}
  else {
    todays_tests <- read_excel("Testing_COVID19_HK_22Aug.xlsx",  sheet = d, skip = 2) %>% 
    filter(`Đơn vị thực hiện` %in% central_codes$`Names of health facilities`) 
  todays_total <- sum(todays_tests$`Kết quả trong ngày`)}
  running_total = c(running_total, todays_total)
}

vietnam_data <- left_join(diagnoses, deaths)
vietnam_data$new_tests <- running_total

# Add latest data
Vietnam <- read.csv("~/Documents/git/covid_vietnam/Vietnam.csv")
newdata <- Vietnam[as.Date(Vietnam$date)>"2020-08-23",c("date","new_diagnoses","new_deaths")]
newdata$new_tests <- NA
vietnam_data <- rbind(vietnam_data, newdata)
vietnam_data$date <- format(vietnam_data$date, "%Y-%m-%d")

write.csv(vietnam_data,"vietnam_data.csv")  

########################################
# Investigating clusters... 
########################################
# North region
ss <- rawcases  %>% group_by(transmit) %>% filter(Region=="North", Type %in% c("Interregional", "Imported")) %>% count(transmit) 
hosp <- rawcases %>% filter(Region=="North", Source=="Domestic", Origin %in% c("Bach Mai hospital","Ha Loi")) %>% count() 

# South region
ss <- rawcases  %>% group_by(transmit) %>% filter(Region=="South", Type %in% c("Interregional", "Imported")) %>% count(transmit) 
hosp <- rawcases %>% filter(Region=="South", Source=="Domestic", Origin %in% c("Bach Mai hospital","Ha Loi")) %>% count() 


#########################################
# Make dataframe with data from Northern region since beginning of epidemic
diagnoses <- data.frame(diagdate = seq(as.Date("2020/2/4"), as.Date("2020/8/22"), "days")) %>%
  left_join(rawcases %>% filter(Region=="North", Source=="Domestic") %>% count(diagdate))  %>%
  rename(date=diagdate,new_diagnoses=n) %>% replace(is.na(.), 0)

deaths <- data.frame(Dead = seq(as.Date("2020/2/4"), as.Date("2020/8/22"), "days")) %>%
  left_join(rawcases %>% filter(Region=="North", Source=="Domestic") %>% count(Dead))  %>%
  rename(date=Dead,new_deaths=n) %>% replace(is.na(.), 0)

## Get testing data
north_codes <- read_excel("Testing_COVID19_HK_22Aug.xlsx", skip = 2) %>%
  rename(en_name=X__1,Region=X__2) %>%
  filter(Region=="North") 

sheets = excel_sheets(path = "Testing_COVID19_HK_22Aug.xlsx")
dates <- sheets[-1]

tests <- data.frame(testdate = seq(as.Date("2020/3/17"), as.Date("2020/8/22"), "days"))

tests <- data.frame(sheet_name = NA,tests = NA)
#tests$sheet_name = NA
#tests$tests = NA

running_total = c()
days = c()
for (d in rev(dates)) {
  if (d %in% c("14_7","20_7","21_7","11_4")) {
    todays_total <- 0
  }
  else {
    todays_tests <- read_excel("Testing_COVID19_HK_22Aug.xlsx",  sheet = d, skip = 2) %>% 
      filter(`Đơn vị thực hiện` %in% north_codes$`Names of health facilities`) 
    todays_total <- sum(todays_tests$`Kết quả trong ngày`,na.rm=T)}
  running_total = c(running_total, todays_total)
  days = c(days,paste("2020/",str_split(d,"_")[[1]][2],"/",str_split(d,"_")[[1]][1],sep=""))
}

tests <- data.frame(date = days,new_tests = running_total)
tests$date <- ymd(tests$date)

vietnam_data <- left_join(diagnoses, deaths)
vietnam_data <- left_join(vietnam_data,tests)

write.csv(vietnam_data,"north_vietnam_data.csv")  
