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
rawcases <- read_excel("1_Case and close contact list_Updates_2August.xlsx",  skip = 6)
rawcases$Region[rawcases$Region=="Highland"] = "Central"
rawcases$Source[rawcases$Source=="Detected case"] = "Domestic"
rawcases$Source[rawcases$Source=="Domestic case"] = "Domestic"
rawcases$Source[rawcases$Source=="Imported case"] = "Imported"
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
data.frame(diagdate = seq(as.Date("2020/1/23"), as.Date("2020/8/2"), "days")) %>%
  left_join(rawcases  %>% group_by(Region, Source, Cluster) %>% count(diagdate)) %>%
  rename(date=diagdate,new_diagnoses=n) %>% filter(!is.na(Region) & !is.na(Source)) %>%
  ggplot(aes(x=date, y=new_diagnoses, fill=Source)) +
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

# Make dataframe with data from central region over the past week
ndf <- data.frame(diagdate = seq(as.Date("2020/7/25"), as.Date("2020/8/2"), "days")) %>%
  left_join(rawcases %>% filter(Region=="Central", Source=="Domestic") %>% count(diagdate))  %>%
  rename(date=diagdate,new_diagnoses=n)

ndf$new_tests <- c(68,9,0,50,434,351,688,NA,NA) # Manually pulled from testing file -- don't seem right though...?
write.csv(ndf,"vietnam_data.csv")  

########################################
# Investigating clusters... 
########################################
# North region
ss <- rawcases  %>% group_by(transmit) %>% filter(Region=="North", Type %in% c("Interregional", "Imported")) %>% count(transmit) 
hosp <- rawcases %>% filter(Region=="North", Source=="Domestic", Origin %in% c("Bach Mai hospital","Ha Loi")) %>% count() 

# South region
ss <- rawcases  %>% group_by(transmit) %>% filter(Region=="South", Type %in% c("Interregional", "Imported")) %>% count(transmit) 
hosp <- rawcases %>% filter(Region=="South", Source=="Domestic", Origin %in% c("Bach Mai hospital","Ha Loi")) %>% count() 
