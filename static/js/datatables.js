// Call the dataTables jQuery plugin

var language_es = {
    "search": "Buscar",
    "info": "Mostrando _START_ a _END_ de _TOTAL_ registros",
    "lengthMenu": "Mostrar _MENU_ registros",
    "zeroRecords": "No se encontraron resultados",
    "emptyTable": "Ningún dato disponible en esta tabla",
    "paginate": {
        "first": "Primero",
        "last": "Último",
        "next": "Siguiente",
        "previous": "Anterior"
    },
    "decimal": ",",
}

$(document).ready(function() {
  $('#notificationsTable').DataTable(
    {
        paging: true,
        stripe: true,
        searching: true,
        scrollX: false,
        pageLength: 50,
        ordering: false,
        order: [[0, 'asc'], [4, 'asc']],
        rowsGroup: [0, 1, 2, 3],
        columnDefs: [
            // Código Particular
            {targets: 0, searchable: true, width: '5%', className: 'dt-right'},
            // Razón Social
            {targets: 1, searchable: true},
            // Teléfono
            {targets: 2, searchable: true, width: '8%'},
            // Saldo cuenta corriente
            {targets: 3, searchable: true, width: '8%', className: 'dt-right'},
            // Fecha de factura
            {targets: 4, searchable: true, width: '5%'},
            // Numero de factura
            {targets: 5, searchable: true, width: '10%'},
            // Monto total de factura
            {targets: 6, searchable: false, width: '8%', className: 'dt-right'},
            // Monto pagado de factura
            {targets: 7, searchable: false, width: '8%', className: 'dt-right'},
            // Saldo de factura
            {targets: 8, searchable: false, width: '8%', className: 'dt-right'},
            // Estado
            {targets: 9, searchable: false, width: '8%', className: 'dt-right'},
            // Acciones
            {targets: 10, searchable: false, width: '10%', className: 'dt-right'},
        ],
        language: language_es
    }
  );
});
