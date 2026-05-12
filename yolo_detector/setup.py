from setuptools import find_packages, setup

package_name = 'yolo_detector'

setup(
    name=package_name,
    version='0.1.0',
    packages=find_packages(exclude=['test']),
    data_files=[
        ('share/ament_index/resource_index/packages',
            ['resource/' + package_name]),
        ('share/' + package_name, ['package.xml']),
    ],
    install_requires=['setuptools'],
    zip_safe=True,
    maintainer='Dito Eka Cahya',
    maintainer_email='dito.eka.cahya@gmail.com',
    description='YOLO object detector using Ultralytics',
    license='BSD-3-Clause',
    entry_points={
        'console_scripts': [
            'yolo_detector_node = yolo_detector.yolo_detector_node:main',
        ],
    },
)
