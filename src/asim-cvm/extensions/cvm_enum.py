import enum


class BusinessTypes(enum.IntEnum):
    wholesale = 1
    gigwork = 2


class RoutePurposes(enum.IntFlag):
    goods = 1
    services = 2
    goods_and_services = 3  # important: this is goods|services
    other = 4


class VehicleTypes(enum.IntEnum):
    car = 1
    light_truck = 2
    med_truck = 3
    heavy_truck = 4
    sidewalk_drone = 5

