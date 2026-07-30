# Home Automation Machine

A small kernel for home automation, meant to run as a single long-lived process (e.g. in
a container on a router) that just glues together inputs and outputs like MQTT, HTTP,
cron, etc.

The main goal is to be able to add, edit, and remove automation scripts by simply
dropping files into a folder or changing them via SSH. These scripts are hot-reloaded
upon change without the need for a service restart.

Scripts do not import or otherwise depend on the kernel at runtime. A broken script
never takes down a previously working one.
