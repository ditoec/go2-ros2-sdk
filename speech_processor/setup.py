import os

from setuptools import setup

package_name = 'speech_processor'


def _knowledge_data_files():
    """Install the bundled sample knowledge base under share/, preserving layout."""
    entries = []
    for root, _dirs, files in os.walk('knowledge'):
        if not files:
            continue
        target = os.path.join('share', package_name, root)
        entries.append((target, [os.path.join(root, f) for f in files]))
    return entries


setup(
    name=package_name,
    version='1.0.0',
    packages=[package_name],
    data_files=[
        ('share/ament_index/resource_index/packages',
            ['resource/' + package_name]),
        ('share/' + package_name, ['package.xml']),
        ('share/' + package_name + '/config', ['config/custom_commands.yaml']),
    ] + _knowledge_data_files(),
    install_requires=[
        'setuptools',
        'requests',
        'pydub',
        'numpy',
        'sounddevice',
        'openai[realtime]',  # [realtime] pulls in websockets — required by client.realtime.connect()
        'google-genai',
        'anthropic',
        'supertonic',
        'duckduckgo-search',
        # Knowledge-base RAG (Modul 3.2). Optional at runtime: knowledge_base.py
        # degrades to OpenAI embeddings or a numpy fallback if this is absent.
        'sentence-transformers',
        # Face recognition (Modul 4.2 — face_recognition_node). insightface bundles
        # SCRFD detection + ArcFace embeddings via onnxruntime. The GPU variant
        # (onnxruntime-gpu) is installed per-platform in the Jetson Docker image;
        # plain onnxruntime here keeps CPU recognition working everywhere.
        'insightface',
        'onnxruntime',
    ],
    zip_safe=True,
    maintainer='Nuralem Abizov',
    maintainer_email='abizov94@gmail.com',
    description='ROS2 package for speech processing including TTS and audio management for Go2 robot',
    license='BSD-3-Clause',
    entry_points={
        'console_scripts': [
            'tts_node = speech_processor.tts_node:main',
            'stt_node = speech_processor.stt_node:main',
            'mic_bridge_node = speech_processor.mic_bridge_node:main',
            'voice_cmd_node = speech_processor.voice_cmd_node:main',
            'gemma_vision_node = speech_processor.gemma_vision_node:main',
            'face_recognition_node = speech_processor.face_recognition_node:main',
            'face_enrollment_node = speech_processor.face_enrollment_node:main',
            'cam_bridge_node = speech_processor.cam_bridge_node:main',
            'mic_diagnostic_node = speech_processor.mic_diagnostic_node:main',
            'follow_me_node = speech_processor.follow_me_node:main',
            'nav_waypoint_node = speech_processor.nav_waypoint_node:main',
            'behavior_coordinator_node = speech_processor.behavior_coordinator_node:main',
            'patrol_node = speech_processor.patrol_node:main',
            'approach_object_node = speech_processor.approach_object_node:main',
            'speech_synthesizer = speech_processor.speech_synthesizer_node:main',
            'audio_manager = speech_processor.audio_manager_node:main',
        ],
    },
) 