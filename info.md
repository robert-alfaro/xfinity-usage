## Setup
1. Install this component
2. Add the following to your `configuration.yaml` 

```yaml
sensor:
  - platform: xfinity
    username: !secret xfinity_email
    password: !secret xfinity_password
```

Here are two lovelace examples:

```yaml
type: entities
entities:
  - entity: sensor.xfinity_usage
```
![entities-card](https://github.com/robert-alfaro/xfinity-usage/raw/master/images/entities-card.png)


```yaml
type: history-graph
entities:
  - entity: sensor.xfinity_usage
hours_to_show: 24
refresh_interval: 3600
```
![history_graph-card](https://github.com/robert-alfaro/xfinity-usage/raw/master/images/history_graph-card.png)
