########################################
# Script for reading in Vietnam's case data 
# and transforming to Covasim format
#
# Date last modified: Dec 11, 2020
########################################

########################################
# Load libraries
########################################
library (readxl)
library (dplyr)
library (reshape2)
library(lubridate)
library(tidyverse)

# Set working directory
setwd(dirname(rstudioapi::getActiveDocumentContext()$path))

########################################
# Import and clean data
########################################
rawcases <- read_excel("rawdata/1_Case and close contact list_Updates_22August_v2.xlsx",  skip = 6)
rawcases$Region[rawcases$Region=="Highland"] = "Central"
rawcases$Source[rawcases$Source=="Detected case"] = "Domestic"
rawcases$Source[rawcases$Source=="Domestic case"] = "Domestic"
rawcases$Source[rawcases$Source=="Imported case"] = "Imported"
rawcases$Source = factor(rawcases$Source)
rawcases$diagdate <- ymd(rawcases$diagdate)


########################################
# Make dataframe with data from central region 
########################################

diagnoses <- data.frame(diagdate = seq(as.Date("2020/6/15"), as.Date("2020/8/22"), "days")) %>%
  left_join(rawcases %>% filter(Region=="Central", Source=="Domestic") %>% count(diagdate))  %>%
  rename(date=diagdate,new_diagnoses=n) %>% replace(is.na(.), 0)

deaths <- data.frame(Dead = seq(as.Date("2020/7/25"), as.Date("2020/8/22"), "days")) %>%
  left_join(rawcases %>% filter(Region=="Central", Source=="Domestic") %>% count(Dead))  %>%
  rename(date=Dead,new_deaths=n) %>% replace(is.na(.), 0)

## Get testing data
central_codes <- read_excel("rawdata/Testing_COVID19_HK_22Aug.xlsx", skip = 2) %>%
  rename(en_name="...3" ,Region="...4" ) %>%
  filter(Region=="Central") 

tests <- data.frame(testdate = seq(as.Date("2020/6/15"), as.Date("2020/8/22"), "days"))
tests$new_tests = NA
dates <- c("15_6", "16_6", "17_6", "18_6", "19_6", "20_6", "21_6", "22_6", "23_6", "24_6", "25_6", "26_6", "27_6", "28_6", "29_6", "30_6","1_7","2_7","3_7","4_7","5_7","6_7","7_7","8_7","9_7","10_7","11_7","12_7","13_7","14_7","15_7","16_7","17_7","18_7","19_7","20_7","21_7","22_7","23_7","24_7","25_7","26_7","27_7","28_7","29_7","30_7","31_7","1_8","2_8","3_8","4_8","5_8","6_8","7_8","8_8","9_8","10_8","11_8","12_8","13_8","14_8","15_8","16_8","17_8","18_8","19_8","20_8","21_8","22_8")

running_total = c()
for (d in dates) {
  if (d %in% c("14_7","20_7","21_7")) {todays_total <- 0}
  else {
    todays_tests <- read_excel("rawdata/Testing_COVID19_HK_22Aug.xlsx",  sheet = d, skip = 2) %>% 
    filter(`Đơn vị thực hiện` %in% central_codes$`Names of health facilities`) 
  todays_total <- sum(todays_tests$`Kết quả trong ngày`)}
  running_total = c(running_total, todays_total)
}

vietnam_data <- left_join(diagnoses, deaths)
vietnam_data$new_tests <- running_total

# Add latest data
orig_data_file <- "rawdata/Vietnam.csv"
if (file.exists(orig_data_file)) {
  Vietnam <- read.csv("rawdata/Vietnam.csv")
  newdata <- Vietnam[as.Date(Vietnam$date)>"2020-08-23Vietnam.cs",c("date","new_diagnoses","new_deaths")]
  newdata$new_tests <- NA
  vietnam_data <- rbind(vietnam_data, newdata)
  vietnam_data$date <- format(vietnam_data$date, "%Y-%m-%d")
  
  write.csv(vietnam_data,"vietnam_data.csv")  
} else {
  message('Note, file not found, not regenerating data file')
}


