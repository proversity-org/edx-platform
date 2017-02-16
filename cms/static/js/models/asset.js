define(['backbone'], function(Backbone) {
  /**
   * Simple model for an asset.
   */
    var Asset = Backbone.Model.extend({
        defaults: {
            display_name: '',
            content_type: '',
            thumbnail: '',
            date_added: '',
            url: '',
            external_url: '',
            portable_url: '',
            locked: false
        },
        url: function() {
            var base = this.urlRoot || this.collection.urlRoot || this.collection.url || console.error(new Error('Asset.url must be defined'));
            if (this.isNew()) return base;
            return base + (base.charAt(base.length - 1) == '/' ? '' : '/') + encodeURIComponent(this.id);
        },
        get_extension: function() {
            var name_segments = this.get('display_name').split('.').reverse();
            var asset_type = (name_segments.length > 1) ? name_segments[0].toUpperCase() : '';
            return asset_type;
        }
    });
    return Asset;
});
