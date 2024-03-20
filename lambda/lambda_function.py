# -*- coding: utf-8 -*-

# This sample demonstrates handling intents from an Alexa skill using the Alexa Skills Kit SDK for Python.
# Please visit https://alexa.design/cookbook for additional examples on implementing slots, dialog management,
# session persistence, api calls, and more.
# This sample is built using the handler classes approach in skill builder.
import logging
import ask_sdk_core.utils as ask_utils
import requests
import json
import math
import os, time
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple, Union
from flight import Flight


from ask_sdk_core.skill_builder import SkillBuilder
from ask_sdk_core.dispatch_components import AbstractRequestHandler
from ask_sdk_core.dispatch_components import AbstractExceptionHandler
from ask_sdk_core.handler_input import HandlerInput

from ask_sdk_model import Response

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)


class LaunchRequestHandler(AbstractRequestHandler):
    """Handler for Skill Launch."""
    def can_handle(self, handler_input):
        # type: (HandlerInput) -> bool

        return ask_utils.is_request_type("LaunchRequest")(handler_input)

    def handle(self, handler_input):
        # type: (HandlerInput) -> Response
        speak_output = "Bem vindo ao Pesquisar Voos, qual é a sua solicitação?"

        return (
            handler_input.response_builder
                .speak(speak_output)
                .ask(speak_output)
                .response
        )


class HelloWorldIntentHandler(AbstractRequestHandler):
    """Handler for Hello World Intent."""
    def can_handle(self, handler_input):
        # type: (HandlerInput) -> bool
        return ask_utils.is_intent_name("HelloWorldIntent")(handler_input)

    def handle(self, handler_input):
        # type: (HandlerInput) -> Response
        speak_output = "Hello World!"

        return (
            handler_input.response_builder
                .speak(speak_output)
                # .ask("add a reprompt if you want to keep the session open for the user to respond")
                .response
        )

class FlightNearIntentHandler(AbstractRequestHandler):
    """Handler for Flight Near Intent."""
    def can_handle(self, handler_input):
        # type: (HandlerInput) -> bool
        return ask_utils.is_intent_name("FlightNearIntent")(handler_input)

    def handle(self, handler_input):
        # type: (HandlerInput) -> Response
        
        ##################################################################
        
        # device_id and token to access which is the timezone device
        deviceId = handler_input.request_envelope.context.system.device.device_id
        apiAccessToken = handler_input.request_envelope.context.system.api_access_token
            
        # urls 
        url_timezone = 'https://api.amazonalexa.com/v2/devices/' + deviceId + '/settings/System.timeZone'
        data_cloud_base_url = "https://data-cloud.flightradar24.com"
        data_live_base_url = "https://data-live.flightradar24.com"
        url_get_fligts = data_cloud_base_url + "/zones/fcgi/feed.js"
        url_flight_details = data_live_base_url + "/clickhandler/?flight={}"
        
        # headers
        headers_timezone =  { 'Authorization': 'Bearer ' + apiAccessToken }
        headers = {
                "accept-encoding": "gzip, utf-8",
                "accept-language": "pt-BR,pt;q=0.9,en-US;q=0.8,en;q=0.7",
                "cache-control": "max-age=0",
                "origin": "https://www.flightradar24.com",
                "referer": "https://www.flightradar24.com/",
                "sec-fetch-dest": "empty",
                "sec-fetch-mode": "cors",
                "sec-fetch-site": "same-site",
                "user-agent": "Mozilla/5.0 (Windows NT 6.1) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/87.0.4280.88 Safari/537.36"
        }
        
        # parameters
        request_params = {}
        request_params["faa"] = "1"
        request_params["satellite"] = "1"
        request_params["mlat"] = "1"
        request_params["flarm"] = "1"
        request_params["adsb"] = "1"
        request_params["gnd"] = "1"
        request_params["air"] = "1"
        request_params["vehicles"] = "1"
        request_params["estimated"] = "1"
        request_params["maxage"] = "14400"
        request_params["gliders"] = "1"
        request_params["stats"] = "1"
        request_params["limit"] = "5000"
        
        # try to access the API Alexa to request timezone device
        response = requests.get(url_timezone, headers = headers_timezone)
        timezone_str = response.content.decode('latin1')
        
        # set the timezone device
        os.environ['TZ'] = timezone_str.replace('"', '') # 'America/Sao_Paulo' 
        
        # get details about geolocation device
        geolocation = handler_input.request_envelope.context.system.device.supported_interfaces.geolocation
        
        # coordinate default while exists tests
        latitude = -23.6765934
        longitude = -46.757523
        radius = 6000
        
        # in case exists the object geolocation
        if geolocation is not None:
            
            # details about geolocation device
            mygeolocation = handler_input.request_envelope.context.geolocation

            # getting latitude and longitute
            latitude = mygeolocation.coordinate.latitude_in_degrees
            longitude = mygeolocation.coordinate.longitude_in_degrees
        
        # prepare the coordinate x radius of max distance 
        bounds = self.get_bounds_by_point(latitude, longitude, radius)
        request_params["bounds"] = bounds.replace(",", "%2C")
        my_flights = []
        
        # getting flights around from the bounds generated
        json_headers = headers.copy()
        if request_params: url_get_fligts += "?" + "&".join(["{}={}".format(k, v) for k, v in request_params.items()])
        response = requests.get(url_get_fligts, request_params, headers = json_headers)
        
        # decode the response object
        content = response.content.decode('latin1')
        content = json.loads(content)
        flights: List[Flight] = list()
        
        for flight_id, flight_info in content.items():
            # Get flights only.
            if not flight_id[0].isnumeric():
                continue
            
            flight = Flight(flight_id, flight_info)
            flights.append(flight)
            
            # Set flight details.
            response = requests.get(url_flight_details.format(flight.id), headers = json_headers)
            content = response.content.decode('latin1')
            content = json.loads(content)
            flight_details = content
            flight.set_flight_details(flight_details)
            
        print(datetime.now())
        time.tzset()
        print(datetime.now())
        # getting nearest flight from all 
        if len(flights) > 0:
            flight = flights[0]
            departured_real_time = flight.time_details.get('real').get('departure')
            departured_real_time = datetime.fromtimestamp(departured_real_time)
            arrival_estimated_time = flight.time_details.get('estimated').get('arrival')
            arrival_estimated_time = datetime.fromtimestamp(arrival_estimated_time)
            
            msg = "Voo " + flight.airline_name + " " + flight.callsign + " decolou de " + flight.origin_airport_country_region_city + " as " + departured_real_time.strftime("%H:%M") + " para " + flight.destination_airport_country_region_city + " com chegada estimada para as " + arrival_estimated_time.strftime("%H:%M") 
        else:
            msg = "Não há voos no momento" 
        print(msg)
        
        ###################################################################
        
        speak_output = msg

        return (
            handler_input.response_builder
                .speak(speak_output)
                # .ask("add a reprompt if you want to keep the session open for the user to respond")
                .response
        )
    
    def get_bounds(self, zone: Dict[str, float]) -> str:
        return "{},{},{},{}".format(zone["tl_y"], zone["br_y"], zone["tl_x"], zone["br_x"])
        
    def get_bounds_by_point(self, latitude: float, longitude: float, radius: float) -> str:
        half_side_in_km = abs(radius) / 1000

        lat = math.radians(latitude)
        lon = math.radians(longitude)

        approx_earth_radius = 6371
        hypotenuse_distance = math.sqrt(2 * (math.pow(half_side_in_km, 2)))

        lat_min = math.asin(
            math.sin(lat) * math.cos(hypotenuse_distance / approx_earth_radius)
            + math.cos(lat)
            * math.sin(hypotenuse_distance / approx_earth_radius)
            * math.cos(225 * (math.pi / 180)),
        )
        lon_min = lon + math.atan2(
            math.sin(225 * (math.pi / 180))
            * math.sin(hypotenuse_distance / approx_earth_radius)
            * math.cos(lat),
            math.cos(hypotenuse_distance / approx_earth_radius)
            - math.sin(lat) * math.sin(lat_min),
        )

        lat_max = math.asin(
            math.sin(lat) * math.cos(hypotenuse_distance / approx_earth_radius)
            + math.cos(lat)
            * math.sin(hypotenuse_distance / approx_earth_radius)
            * math.cos(45 * (math.pi / 180)),
        )
        lon_max = lon + math.atan2(
            math.sin(45 * (math.pi / 180))
            * math.sin(hypotenuse_distance / approx_earth_radius)
            * math.cos(lat),
            math.cos(hypotenuse_distance / approx_earth_radius)
            - math.sin(lat) * math.sin(lat_max),
        )

        rad2deg = math.degrees

        zone = {
            "tl_y": rad2deg(lat_max),
            "br_y": rad2deg(lat_min),
            "tl_x": rad2deg(lon_min),
            "br_x": rad2deg(lon_max)
        }
        return self.get_bounds(zone)

class CompanyCodeIntentHandler(AbstractRequestHandler):
    """Handler for Company Code Intent."""
    def can_handle(self, handler_input):
        # type: (HandlerInput) -> bool
        return ask_utils.is_intent_name("CompanyCodeIntent")(handler_input)

    def handle(self, handler_input):
        # type: (HandlerInput) -> Response
        name_company = handler_input.request_envelope.request.intent.slots['name_company'].value
        
        ############################ access API FlightRadar24 ##################################
        
        flightradar_base_url = "https://www.flightradar24.com"
        airlines_data_url = flightradar_base_url + "/_json/airlines.php"
        headers = {
                "accept-encoding": "gzip, utf-8",
                "accept-language": "pt-BR,pt;q=0.9,en-US;q=0.8,en;q=0.7",
                "cache-control": "max-age=0",
                "origin": "https://www.flightradar24.com",
                "referer": "https://www.flightradar24.com/",
                "sec-fetch-dest": "empty",
                "sec-fetch-mode": "cors",
                "sec-fetch-site": "same-site",
                "user-agent": "Mozilla/5.0 (Windows NT 6.1) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/87.0.4280.88 Safari/537.36"
            }
        
        json_headers = headers.copy()
        
        response = requests.get(airlines_data_url, headers = json_headers)
        content = response.content.decode('latin1')
        companies = json.loads(content)["rows"]
        companies_found = []
        for company in companies:
            if company["Name"].lower() == name_company.lower():
                print(company["Name"], name_company)
                companies_found.append(company)
                
        if len(companies_found) > 0:
            code_company = companies_found[0]["Code"]
            message = "O código da Companhia aérea " + name_company + " é " + code_company
        else:
            message = "Não tem companhia com esse nome"
        ###################################################################################### 
        
        speak_output = message
        
        return (
            handler_input.response_builder
                .speak(speak_output)
                # .ask("add a reprompt if you want to keep the session open for the user to respond")
                .response
        )   

class SearchFlightIntentHandler(AbstractRequestHandler):
    """Handler for Search Flight Intent."""
    def can_handle(self, handler_input):
        # type: (HandlerInput) -> bool
        return ask_utils.is_intent_name("SearchFlightIntent")(handler_input)

    def handle(self, handler_input):
        # type: (HandlerInput) -> Response
        flight_code = handler_input.request_envelope.request.intent.slots['flight_code'].value
        
        ############################ access API FlightRadar24 ##################################
        
        # device_id and token to access which is the timezone device
        deviceId = handler_input.request_envelope.context.system.device.device_id
        apiAccessToken = handler_input.request_envelope.context.system.api_access_token
        
        # urls 
        data_live_base_url = "https://data-live.flightradar24.com"
        url_flight_details = data_live_base_url + "/clickhandler/?flight={}"
        
        headers = {
                "accept-encoding": "gzip, utf-8",
                "accept-language": "pt-BR,pt;q=0.9,en-US;q=0.8,en;q=0.7",
                "cache-control": "max-age=0",
                "origin": "https://www.flightradar24.com",
                "referer": "https://www.flightradar24.com/",
                "sec-fetch-dest": "empty",
                "sec-fetch-mode": "cors",
                "sec-fetch-site": "same-site",
                "user-agent": "Mozilla/5.0 (Windows NT 6.1) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/87.0.4280.88 Safari/537.36"
        }
        
        json_headers = headers.copy()

        print(flight_code)
        flight_ = self.search(flight_code)
        if len(flight_.get('live')) > 0:
            flight_id = flight_.get('live')[0].get('id')
            info = self.populate_flight(flight_)
            flight = Flight(flight_id, info)
            response = requests.get(url_flight_details.format(flight.id), headers = json_headers) 
            content = response.content.decode('latin1')
            content = json.loads(content)
            flight_details = content
            timezone_origin = flight_details.get('airport').get('origin').get('timezone').get('name')
            timezone_dest = flight_details.get('airport').get('destination').get('timezone').get('name')
            flight.set_flight_details(flight_details)
            departured_real_time = flight.time_details.get('real').get('departure')
            os.environ['TZ'] = timezone_origin
            time.tzset()
            departured_real_time = datetime.fromtimestamp(departured_real_time)
            arrival_estimated_time = flight.time_details.get('estimated').get('arrival')
            os.environ['TZ'] = timezone_dest
            time.tzset()
            arrival_estimated_time = datetime.fromtimestamp(arrival_estimated_time)
            
            message = "Voo " + flight.airline_name + " " + flight.callsign + " decolou de " + flight.origin_airport_country_region_city + " as " + departured_real_time.strftime("%H:%M") + " horário local para " + flight.destination_airport_country_region_city + " com chegada estimada para as " + arrival_estimated_time.strftime("%H:%M") + " horário local"
            
        elif len(flight_.get('schedule')) > 0:
            message = 'Status do voo consultado é AGENDADO!'
        else:
            message = 'Voo não encontrado!'
        
        print(message)
        ###################################################################################### 
        
        speak_output = message
        
        return (
            handler_input.response_builder
                .speak(speak_output)
                # .ask("add a reprompt if you want to keep the session open for the user to respond")
                .response
        )  
        
    def populate_flight(self, info) -> List:
        result = []
        for i in range(0,19):
            result.append('')
        result[1]  = info.get('live')[0].get('detail').get('lat')
        result[2]  = info.get('live')[0].get('detail').get('lon')
        result[8]  = info.get('live')[0].get('detail').get('ac_type')
        result[9]  = info.get('live')[0].get('detail').get('reg')
        result[11] = info.get('live')[0].get('detail').get('schd_from')
        result[12] = info.get('live')[0].get('detail').get('schd_to')
        if info.get('live')[0].get('detail').get('flight') is not None:
            result[13] = info.get('live')[0].get('detail').get('flight')
        else:
            result[13] = info.get('live')[0].get('detail').get('callsign')
        result[16] = info.get('live')[0].get('detail').get('callsign')
        result[18] = info.get('live')[0].get('detail').get('operator')
        
        return result
        
    def search(self, flight_code) -> Dict:
        flightradar_base_url = "https://www.flightradar24.com"
        search_data_url = flightradar_base_url + "/v1/search/web/find?query={}&limit=50"
        
        headers = {
                "accept-encoding": "gzip, utf-8",
                "accept-language": "pt-BR,pt;q=0.9,en-US;q=0.8,en;q=0.7",
                "cache-control": "max-age=0",
                "origin": "https://www.flightradar24.com",
                "referer": "https://www.flightradar24.com/",
                "sec-fetch-dest": "empty",
                "sec-fetch-mode": "cors",
                "sec-fetch-site": "same-site",
                "user-agent": "Mozilla/5.0 (Windows NT 6.1) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/87.0.4280.88 Safari/537.36"
        }
        
        json_headers = headers.copy()
        
        response = requests.get(search_data_url.format(flight_code), headers = json_headers)
        content = response.content.decode('latin1')
        content = json.loads(content)
        results = content.get("results", [])
        stats = content.get("stats", {})
        
        i = 0
        counted_total = 0
        data = {}
        for name, count in stats.get("count", {}).items():
            data[name] = []
            while i < counted_total + count and i < len(results):
                data[name].append(results[i])
                i += 1
            counted_total += count
            
        return data

class HelpIntentHandler(AbstractRequestHandler):
    """Handler for Help Intent."""
    def can_handle(self, handler_input):
        # type: (HandlerInput) -> bool
        return ask_utils.is_intent_name("AMAZON.HelpIntent")(handler_input)

    def handle(self, handler_input):
        # type: (HandlerInput) -> Response
        speak_output = "You can say hello to me! How can I help?"

        return (
            handler_input.response_builder
                .speak(speak_output)
                .ask(speak_output)
                .response
        )


class CancelOrStopIntentHandler(AbstractRequestHandler):
    """Single handler for Cancel and Stop Intent."""
    def can_handle(self, handler_input):
        # type: (HandlerInput) -> bool
        return (ask_utils.is_intent_name("AMAZON.CancelIntent")(handler_input) or
                ask_utils.is_intent_name("AMAZON.StopIntent")(handler_input))

    def handle(self, handler_input):
        # type: (HandlerInput) -> Response
        speak_output = "Até mais!"

        return (
            handler_input.response_builder
                .speak(speak_output)
                .response
        )

class FallbackIntentHandler(AbstractRequestHandler):
    """Single handler for Fallback Intent."""
    def can_handle(self, handler_input):
        # type: (HandlerInput) -> bool
        return ask_utils.is_intent_name("AMAZON.FallbackIntent")(handler_input)

    def handle(self, handler_input):
        # type: (HandlerInput) -> Response
        logger.info("In FallbackIntentHandler")
        speech = "Hmm, não tenho certeza. Você pode dizer Olá ou Ajuda. O que você gostaria de fazer?"
        reprompt = "Eu não entendi isso. Com o que posso ajudar?"

        return handler_input.response_builder.speak(speech).ask(reprompt).response

class SessionEndedRequestHandler(AbstractRequestHandler):
    """Handler for Session End."""
    def can_handle(self, handler_input):
        # type: (HandlerInput) -> bool
        return ask_utils.is_request_type("SessionEndedRequest")(handler_input)

    def handle(self, handler_input):
        # type: (HandlerInput) -> Response

        # Any cleanup logic goes here.

        return handler_input.response_builder.response


class IntentReflectorHandler(AbstractRequestHandler):
    """The intent reflector is used for interaction model testing and debugging.
    It will simply repeat the intent the user said. You can create custom handlers
    for your intents by defining them above, then also adding them to the request
    handler chain below.
    """
    def can_handle(self, handler_input):
        # type: (HandlerInput) -> bool
        return ask_utils.is_request_type("IntentRequest")(handler_input)

    def handle(self, handler_input):
        # type: (HandlerInput) -> Response
        intent_name = ask_utils.get_intent_name(handler_input)
        speak_output = "Você acabou de acionar " + intent_name + "."

        return (
            handler_input.response_builder
                .speak(speak_output)
                # .ask("add a reprompt if you want to keep the session open for the user to respond")
                .response
        )


class CatchAllExceptionHandler(AbstractExceptionHandler):
    """Generic error handling to capture any syntax or routing errors. If you receive an error
    stating the request handler chain is not found, you have not implemented a handler for
    the intent being invoked or included it in the skill builder below.
    """
    def can_handle(self, handler_input, exception):
        # type: (HandlerInput, Exception) -> bool
        return True

    def handle(self, handler_input, exception):
        # type: (HandlerInput, Exception) -> Response
        logger.error(exception, exc_info=True)

        speak_output = "Desculpe, tive problemas para fazer o que você pediu. Por favor, tente novamente."

        return (
            handler_input.response_builder
                .speak(speak_output)
                .ask(speak_output)
                .response
        )

# The SkillBuilder object acts as the entry point for your skill, routing all request and response
# payloads to the handlers above. Make sure any new handlers or interceptors you've
# defined are included below. The order matters - they're processed top to bottom.


sb = SkillBuilder()

sb.add_request_handler(LaunchRequestHandler())

sb.add_request_handler(FlightNearIntentHandler())
sb.add_request_handler(CompanyCodeIntentHandler())
sb.add_request_handler(SearchFlightIntentHandler())

sb.add_request_handler(HelloWorldIntentHandler())
sb.add_request_handler(HelpIntentHandler())
sb.add_request_handler(CancelOrStopIntentHandler())
sb.add_request_handler(FallbackIntentHandler())
sb.add_request_handler(SessionEndedRequestHandler())
sb.add_request_handler(IntentReflectorHandler()) # make sure IntentReflectorHandler is last so it doesn't override your custom intent handlers

sb.add_exception_handler(CatchAllExceptionHandler())

lambda_handler = sb.lambda_handler()